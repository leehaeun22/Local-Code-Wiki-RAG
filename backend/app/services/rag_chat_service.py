import logging
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.code_chunk import CodeChunk
from app.models.document import Document
from app.models.message_reference import MessageReference
from app.schemas.chat_schema import ChatRequest, ChatSessionCreate
from app.services.embedding_service import search_project_chunks
from app.services.project_service import get_project


logger = logging.getLogger(__name__)

MAX_CONTEXTS = 5
TOKEN_PATTERN = re.compile(r"[가-힣]+|[A-Za-z0-9_./-]+", flags=re.UNICODE)
NO_REFERENCES_MESSAGE = "참고 근거가 없습니다. 먼저 scan/chunk/document generation을 실행하세요."
SYSTEM_PROMPT = """You are a repository onboarding assistant.
Rules:
- Answer only using the provided context.
- If the context does not contain the answer, say that you do not know.
- Include relevant file paths and line numbers.
- Do not force-translate technical terms.
"""


class RagChatError(Exception):
    pass


def create_chat_session(db: Session, project_id: str, payload: ChatSessionCreate) -> ChatSession:
    get_project(db, project_id)
    session = ChatSession(project_id=project_id, user_id=None, title=payload.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_chat_sessions(db: Session, project_id: str) -> list[ChatSession]:
    get_project(db, project_id)
    return list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.project_id == project_id)
            .order_by(ChatSession.created_at.desc()),
        ).all(),
    )


def list_chat_messages(db: Session, project_id: str, session_id: str) -> list[ChatMessage]:
    _get_session(db, project_id, session_id)
    return list(
        db.scalars(
            select(ChatMessage)
            .options(selectinload(ChatMessage.references))
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at),
        ).all(),
    )


def answer_chat(db: Session, project_id: str, payload: ChatRequest) -> tuple[ChatSession, ChatMessage, ChatMessage]:
    get_project(db, project_id)
    session = (
        _get_session(db, project_id, payload.session_id)
        if payload.session_id
        else create_chat_session(db, project_id, ChatSessionCreate(title=payload.question[:80]))
    )

    try:
        chunk_count = _count_code_chunks(db, project_id)
        document_count = _count_documents(db, project_id)
        search_results = _resolve_context(
            db=db,
            project_id=project_id,
            question=payload.question,
            chunk_count=chunk_count,
            document_count=document_count,
        )
        logger.debug(
            "rag_context query=%s project_id=%s chunk_count=%s document_count=%s selected_context_count=%s",
            payload.question,
            project_id,
            chunk_count,
            document_count,
            len(search_results),
        )

        context = _build_context(search_results)
        answer = _generate_answer(
            question=payload.question,
            context=context,
            language=payload.language,
            search_results=search_results,
            chunk_count=chunk_count,
            document_count=document_count,
        )

        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            content=payload.question,
            language=payload.language,
        )
        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            language=payload.language,
        )
        db.add(user_message)
        db.add(assistant_message)
        db.flush()

        for result in search_results:
            reference = MessageReference(
                message_id=assistant_message.id,
                file_id=result.get("file_id"),
                chunk_id=result.get("chunk_id"),
                document_id=result.get("document_id"),
                file_path=result.get("file_path"),
                start_line=result.get("start_line"),
                end_line=result.get("end_line"),
                snippet=_snippet(result["content"]),
                score=result.get("score"),
                summary=_reference_summary(result),
            )
            db.add(reference)

        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)
        assistant_message = _get_message(db, assistant_message.id)
        session = _get_session(db, project_id, session.id)

        return session, user_message, assistant_message
    except RagChatError as exc:
        db.rollback()
        raise RagChatError(str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise RagChatError(str(exc)) from exc


def _get_session(db: Session, project_id: str, session_id: str) -> ChatSession:
    session = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.project_id == project_id,
        ),
    )

    if session is None:
        raise RagChatError("Chat session not found.")

    return session


def _get_message(db: Session, message_id: str) -> ChatMessage:
    message = db.scalar(
        select(ChatMessage)
        .options(selectinload(ChatMessage.references))
        .where(ChatMessage.id == message_id),
    )

    if message is None:
        raise RagChatError("Chat message not found.")

    return message


def _count_code_chunks(db: Session, project_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(CodeChunk).where(CodeChunk.project_id == project_id),
    ) or 0


def _count_documents(db: Session, project_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Document).where(Document.project_id == project_id),
    ) or 0


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token.strip()) > 1]


def _keyword_match_score(query: str, *fields: str) -> float:
    query_text = (query or "").strip().lower()
    tokens = _tokenize(query_text)

    if not tokens:
        return 0.0

    haystacks = [field.lower() for field in fields if field]
    if not haystacks:
        return 0.0

    score = 0.0
    full_text = "\n".join(haystacks)

    if query_text and query_text in full_text:
        score += 4.0

    for token in tokens:
        token_matches = sum(text.count(token) for text in haystacks)
        if token_matches > 0:
            score += min(token_matches, 3) * 1.25

    return score


def _chunk_score(query: str, chunk: CodeChunk) -> float:
    file_path = chunk.file.file_path
    content_score = _keyword_match_score(query, chunk.content)
    path_score = _keyword_match_score(query, file_path) * 1.4
    line_hint_score = 0.2 if chunk.chunk_index == 0 else 0.0
    return content_score + path_score + line_hint_score


def _document_score(query: str, document: Document) -> float:
    title_score = _keyword_match_score(query, document.title) * 1.6
    type_score = _keyword_match_score(query, document.document_type.replace("_", " ")) * 1.2
    content_score = _keyword_match_score(query, document.content)
    return title_score + type_score + content_score


def _resolve_context(
    db: Session,
    project_id: str,
    question: str,
    chunk_count: int,
    document_count: int,
) -> list[dict[str, Any]]:
    if chunk_count > 0:
        return _select_chunk_context(db, project_id, question)

    if document_count > 0:
        return _select_document_context(db, project_id, question)

    return []


def _select_chunk_context(db: Session, project_id: str, question: str) -> list[dict[str, Any]]:
    chunks = list(
        db.scalars(
            select(CodeChunk)
            .options(selectinload(CodeChunk.file))
            .where(CodeChunk.project_id == project_id)
            .order_by(CodeChunk.file_id, CodeChunk.chunk_index),
        ).all(),
    )

    vector_results = search_project_chunks(
        db=db,
        project_id=project_id,
        query=question,
        top_k=MAX_CONTEXTS,
    )
    vector_by_chunk_id = {result.get("chunk_id"): result for result in vector_results if result.get("chunk_id")}

    ranked: list[dict[str, Any]] = []
    for chunk in chunks:
        score = _chunk_score(question, chunk)
        vector_result = vector_by_chunk_id.get(chunk.id)
        if vector_result and vector_result.get("distance") is not None:
            score += _vector_bonus(vector_result["distance"])
        ranked.append(
            {
                "reference_type": "code_chunk",
                "chunk_id": chunk.id,
                "document_id": None,
                "file_id": chunk.file_id,
                "file_path": chunk.file.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
                "score": round(score, 4),
                "metadata": {"file_path": chunk.file.file_path},
            },
        )

    ranked.sort(key=lambda item: (item["score"], item["start_line"] is not None), reverse=True)
    selected = [item for item in ranked if item["score"] > 0][:MAX_CONTEXTS]

    if selected:
        return selected

    return _project_overview_chunk_context(chunks)


def _select_document_context(db: Session, project_id: str, question: str) -> list[dict[str, Any]]:
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.updated_at.desc()),
        ).all(),
    )

    ranked = [
        {
            "reference_type": "document",
            "chunk_id": None,
            "document_id": document.id,
            "file_id": document.file_id,
            "file_path": f"documents/{document.document_type}.{document.language}.md",
            "start_line": None,
            "end_line": None,
            "content": document.content,
            "score": round(_document_score(question, document), 4),
            "metadata": {"document_type": document.document_type, "title": document.title},
        }
        for document in documents
    ]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    selected = [item for item in ranked if item["score"] > 0][:MAX_CONTEXTS]

    if selected:
        return selected

    return _project_overview_document_context(documents)


def _project_overview_chunk_context(chunks: list[CodeChunk]) -> list[dict[str, Any]]:
    preferred = sorted(
        chunks,
        key=lambda chunk: (
            "readme" not in chunk.file.file_path.lower(),
            chunk.file.file_path.count("/"),
            chunk.chunk_index,
        ),
    )[:MAX_CONTEXTS]
    return [
        {
            "reference_type": "code_chunk",
            "chunk_id": chunk.id,
            "document_id": None,
            "file_id": chunk.file_id,
            "file_path": chunk.file.file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
            "score": 0.01,
            "metadata": {"file_path": chunk.file.file_path},
        }
        for chunk in preferred
    ]


def _project_overview_document_context(documents: list[Document]) -> list[dict[str, Any]]:
    preferred = sorted(
        documents,
        key=lambda document: (
            document.document_type != "overview",
            document.document_type != "folder_structure",
            document.updated_at,
        ),
        reverse=False,
    )[:MAX_CONTEXTS]
    return [
        {
            "reference_type": "document",
            "chunk_id": None,
            "document_id": document.id,
            "file_id": document.file_id,
            "file_path": f"documents/{document.document_type}.{document.language}.md",
            "start_line": None,
            "end_line": None,
            "content": document.content,
            "score": 0.01,
            "metadata": {"document_type": document.document_type, "title": document.title},
        }
        for document in preferred
    ]


def _vector_bonus(distance: float) -> float:
    return max(0.0, 2.5 - min(distance, 2.5))


def _build_context(search_results: list[dict[str, Any]]) -> str:
    if not search_results:
        return "No context was retrieved."

    blocks = []
    for index, result in enumerate(search_results[:MAX_CONTEXTS], start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{index}] {_reference_summary(result)}",
                    result["content"],
                ],
            ),
        )

    return "\n\n---\n\n".join(blocks)


def _generate_answer(
    question: str,
    context: str,
    language: str,
    search_results: list[dict[str, Any]],
    chunk_count: int,
    document_count: int,
) -> str:
    if chunk_count == 0 and document_count == 0:
        return NO_REFERENCES_MESSAGE

    if not settings.openai_api_key:
        return _generate_local_answer(question=question, language=language, search_results=search_results)

    from openai import OpenAI

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        language_instruction = "Answer in Korean." if language == "ko" else "Answer in English."
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n{language_instruction}"},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if content:
            return content
    except Exception:
        pass

    return _generate_local_answer(question=question, language=language, search_results=search_results)


def _generate_local_answer(question: str, language: str, search_results: list[dict[str, Any]]) -> str:
    if not search_results:
        return NO_REFERENCES_MESSAGE if language == "ko" else (
            "No references are available. Run scan, chunk generation, and document generation first."
        )

    reference_summaries = [_reference_summary(result) for result in search_results[:3]]
    evidence_lines = [_snippet(result["content"], max_length=220) for result in search_results[:3]]

    if language == "ko":
        lines = [
            "프로젝트 요약:",
            "이 답변은 저장된 context를 점수화해 선택한 로컬 fallback 응답입니다.",
            f"질문: {question}",
            "",
            "관련 근거:",
        ]
        lines.extend(f"- {summary}" for summary in reference_summaries)
        lines.append("")
        lines.append("질문과 관련 있어 보이는 내용:")
        lines.extend(f"- {evidence}" for evidence in evidence_lines if evidence)
        return "\n".join(lines)

    lines = [
        "Project summary:",
        "This is a local fallback answer built from ranked repository context.",
        f"Question: {question}",
        "",
        "Relevant references:",
    ]
    lines.extend(f"- {summary}" for summary in reference_summaries)
    lines.append("")
    lines.append("Potential evidence related to your question:")
    lines.extend(f"- {evidence}" for evidence in evidence_lines if evidence)
    return "\n".join(lines)


def _reference_summary(result: dict[str, Any]) -> str:
    file_path = result.get("file_path") or "Generated document"
    start_line = result.get("start_line")
    end_line = result.get("end_line")
    metadata = result.get("metadata") or {}

    if result.get("reference_type") == "document" or start_line is None or end_line is None:
        title = metadata.get("title")
        return f"{file_path} ({title})" if title else file_path

    return f"{file_path}:{start_line}-{end_line}"


def _snippet(content: str, max_length: int = 500) -> str:
    normalized = " ".join(content.strip().split())
    return normalized[:max_length]

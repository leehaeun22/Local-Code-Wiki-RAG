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


class RagChatError(Exception):
    pass


SYSTEM_PROMPT = """You are a repository onboarding assistant.
Rules:
- Answer only using the provided context.
- If the context does not contain the answer, say that you do not know.
- Include relevant file paths and line numbers.
- Do not force-translate technical terms.
"""

NO_REFERENCES_MESSAGE = "참고 근거가 없습니다. 먼저 scan/chunk/document generation을 실행하세요."


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
        code_chunk_count = _count_code_chunks(db, project_id)
        document_count = _count_documents(db, project_id)
        search_results = _resolve_context(
            db=db,
            project_id=project_id,
            question=payload.question,
            top_k=payload.top_k,
            code_chunk_count=code_chunk_count,
            document_count=document_count,
        )
        logger.debug(
            "RAG context resolved project_id=%s code_chunks=%s documents=%s selected_references=%s",
            project_id,
            code_chunk_count,
            document_count,
            len(search_results),
        )

        context = _build_context(search_results)
        answer = _generate_answer(
            question=payload.question,
            context=context,
            language=payload.language,
            search_results=search_results,
            code_chunk_count=code_chunk_count,
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
                score=_score_from_distance(result.get("distance")),
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


def _resolve_context(
    db: Session,
    project_id: str,
    question: str,
    top_k: int,
    code_chunk_count: int,
    document_count: int,
) -> list[dict[str, Any]]:
    if code_chunk_count > 0:
        chunk_results = search_project_chunks(
            db=db,
            project_id=project_id,
            query=question,
            top_k=top_k,
        )
        if chunk_results:
            return chunk_results

        return _fallback_code_chunk_context(db, project_id, question, top_k)

    if document_count > 0:
        return _fallback_document_context(db, project_id, question, top_k)

    return []


def _build_context(search_results: list[dict[str, Any]]) -> str:
    if not search_results:
        return "No context was retrieved."

    blocks = []

    for index, result in enumerate(search_results, start=1):
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
    code_chunk_count: int,
    document_count: int,
) -> str:
    if code_chunk_count == 0 and document_count == 0:
        return NO_REFERENCES_MESSAGE

    if not settings.openai_api_key:
        return _generate_local_answer(
            question=question,
            language=language,
            search_results=search_results,
        )

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

    return _generate_local_answer(
        question=question,
        language=language,
        search_results=search_results,
    )


def _generate_local_answer(
    question: str,
    language: str,
    search_results: list[dict[str, Any]],
) -> str:
    if not search_results:
        return NO_REFERENCES_MESSAGE if language == "ko" else (
            "No references are available. Run scan, chunk generation, and document generation first."
        )

    reference_summaries = [_reference_summary(result) for result in search_results[:3]]
    evidence_lines = [_snippet(result["content"], max_length=220) for result in search_results[:2]]

    if language == "ko":
        lines = [
            "프로젝트 요약:",
            "이 답변은 저장된 code chunks 또는 documents를 기준으로 생성한 로컬 fallback 응답입니다.",
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
        "This is a local fallback answer generated from stored code chunks or documents.",
        f"Question: {question}",
        "",
        "Relevant references:",
    ]
    lines.extend(f"- {summary}" for summary in reference_summaries)
    lines.append("")
    lines.append("Potential evidence related to your question:")
    lines.extend(f"- {evidence}" for evidence in evidence_lines if evidence)
    return "\n".join(lines)


def _fallback_code_chunk_context(
    db: Session,
    project_id: str,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    chunks = list(
        db.scalars(
            select(CodeChunk)
            .options(selectinload(CodeChunk.file))
            .where(CodeChunk.project_id == project_id)
            .order_by(CodeChunk.created_at.desc()),
        ).all(),
    )
    ranked = sorted(
        chunks,
        key=lambda chunk: (_score_text_for_query(query, f"{chunk.file.file_path}\n{chunk.content}"), chunk.created_at),
        reverse=True,
    )
    chosen = ranked[:top_k] if ranked else []

    if chosen and _score_text_for_query(query, f"{chosen[0].file.file_path}\n{chosen[0].content}") <= 0:
        chosen = chunks[:top_k]

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
            "distance": None,
            "metadata": {"file_path": chunk.file.file_path},
        }
        for chunk in chosen
    ]


def _fallback_document_context(
    db: Session,
    project_id: str,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.updated_at.desc()),
        ).all(),
    )
    ranked = sorted(
        documents,
        key=lambda document: (_score_text_for_query(query, f"{document.title}\n{document.content}"), document.updated_at),
        reverse=True,
    )
    chosen = ranked[:top_k] if ranked else []

    if chosen and _score_text_for_query(query, f"{chosen[0].title}\n{chosen[0].content}") <= 0:
        chosen = documents[:top_k]

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
            "distance": None,
            "metadata": {"document_type": document.document_type, "title": document.title},
        }
        for document in chosen
    ]


def _score_text_for_query(query: str, text: str) -> float:
    tokens = [token for token in re.findall(r"\w+", query.lower(), flags=re.UNICODE) if len(token) > 1]

    if not tokens:
        return 0.0

    haystack = text.lower()
    score = 0.0

    for token in tokens:
        if token in haystack:
            score += 1.0

    if query.lower() in haystack:
        score += 2.0

    return score


def _reference_summary(result: dict[str, Any]) -> str:
    file_path = result.get("file_path") or "Generated document"
    start_line = result.get("start_line")
    end_line = result.get("end_line")
    metadata = result.get("metadata") or {}

    if result.get("reference_type") == "document" or (start_line is None or end_line is None):
        title = metadata.get("title")
        return f"{file_path} ({title})" if title else file_path

    return f"{file_path}:{start_line}-{end_line}"


def _snippet(content: str, max_length: int = 500) -> str:
    normalized = " ".join(content.strip().split())
    return normalized[:max_length]


def _score_from_distance(distance: float | None) -> float | None:
    if distance is None:
        return None

    return 1 / (1 + distance)

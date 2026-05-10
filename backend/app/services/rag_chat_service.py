import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.message_reference import MessageReference
from app.schemas.chat_schema import ChatRequest, ChatSessionCreate
from app.services.embedding_service import EmbeddingGenerationError, search_project_chunks
from app.services.project_service import ProjectNotFoundError, get_project


class RagChatError(Exception):
    pass


SYSTEM_PROMPT = """You are a repository onboarding assistant.
Rules:
- Answer only using the provided context.
- If the context does not contain the answer, say that you do not know.
- Include relevant file paths and line numbers.
- Do not force-translate technical terms.
"""


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
        search_results = search_project_chunks(
            db=db,
            project_id=project_id,
            query=payload.question,
            top_k=payload.top_k,
        )
        search_results = _with_document_results(
            db=db,
            project_id=project_id,
            query=payload.question,
            top_k=payload.top_k,
            chunk_results=search_results,
        )
        context = _build_context(search_results)
        answer = _generate_answer(
            question=payload.question,
            context=context,
            language=payload.language,
            search_results=search_results,
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
    except (EmbeddingGenerationError, RagChatError) as exc:
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
) -> str:
    if not settings.openai_api_key:
        return _generate_local_answer(question=question, context=context, language=language, search_results=search_results)

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

    return _generate_local_answer(question=question, context=context, language=language, search_results=search_results)


def _generate_local_answer(
    question: str,
    context: str,
    language: str,
    search_results: list[dict[str, Any]],
) -> str:
    del question, context

    if language == "ko":
        if not search_results:
            return (
                "저장된 code_chunks 또는 documents에서 관련 내용을 찾지 못했습니다. "
                "먼저 scan, chunk generation, document generation을 실행한 뒤 다시 질문하세요."
            )

        lines = [
            "OpenAI API 키가 없어 로컬 저장소 context만 사용해 답변합니다.",
            "찾은 참고 근거:",
        ]
        lines.extend(f"- {_reference_summary(result)}" for result in search_results[:3])
        lines.append("더 자세한 설명이 필요하면 OpenAI API 키와 ChromaDB를 설정한 뒤 다시 질문하세요.")
        return "\n".join(lines)

    if not search_results:
        return (
            "I couldn't find relevant content in stored code chunks or documents. "
            "Run scan, chunk generation, and document generation first, then ask again."
        )

    lines = [
        "OpenAI API key is not configured, so this answer is based only on local repository context.",
        "References found:",
    ]
    lines.extend(f"- {_reference_summary(result)}" for result in search_results[:3])
    lines.append("For a fuller answer, configure an OpenAI API key and ChromaDB, then ask again.")
    return "\n".join(lines)


def _with_document_results(
    db: Session,
    project_id: str,
    query: str,
    top_k: int,
    chunk_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(chunk_results) >= top_k:
        return chunk_results[:top_k]

    document_results = _fallback_search_project_documents(db, project_id, query, top_k)
    combined = [*chunk_results]
    existing_document_ids = {result.get("document_id") for result in combined if result.get("document_id")}

    for result in document_results:
        document_id = result.get("document_id")

        if document_id in existing_document_ids:
            continue

        combined.append(result)

        if len(combined) >= top_k:
            break

    return combined


def _fallback_search_project_documents(
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
    ranked_documents = sorted(
        documents,
        key=lambda document: (_score_text_for_query(query, f"{document.title}\n{document.content}"), document.updated_at),
        reverse=True,
    )
    results: list[dict[str, Any]] = []

    for document in ranked_documents[:top_k]:
        score = _score_text_for_query(query, f"{document.title}\n{document.content}")

        if score <= 0:
            continue

        results.append(
            {
                "chunk_id": None,
                "document_id": document.id,
                "file_id": document.file_id,
                "file_path": f"documents/{document.document_type}.{document.language}.md",
                "start_line": None,
                "end_line": None,
                "content": document.content,
                "distance": 1 / (1 + score),
                "metadata": {"document_type": document.document_type, "title": document.title},
            },
        )

    return results


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

    if start_line is None or end_line is None:
        metadata = result.get("metadata") or {}
        title = metadata.get("title")
        return f"{file_path} ({title})" if title else file_path

    return f"{file_path}:{start_line}-{end_line}"


def _snippet(content: str, max_length: int = 500) -> str:
    normalized = content.strip()
    return normalized[:max_length]


def _score_from_distance(distance: float | None) -> float | None:
    if distance is None:
        return None

    return 1 / (1 + distance)

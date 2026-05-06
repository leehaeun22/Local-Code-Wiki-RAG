from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
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
        context = _build_context(search_results)
        answer = _generate_answer(
            question=payload.question,
            context=context,
            language=payload.language,
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
                file_id=result["file_id"],
                chunk_id=result["chunk_id"],
                document_id=None,
                file_path=result["file_path"],
                start_line=result["start_line"],
                end_line=result["end_line"],
                snippet=_snippet(result["content"]),
                score=_score_from_distance(result.get("distance")),
                summary=f"{result['file_path']}:{result['start_line']}-{result['end_line']}",
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
                    f"[{index}] {result['file_path']}:{result['start_line']}-{result['end_line']}",
                    result["content"],
                ],
            ),
        )

    return "\n\n---\n\n".join(blocks)


def _generate_answer(question: str, context: str, language: str) -> str:
    if not settings.openai_api_key:
        raise RagChatError("OPENAI_API_KEY is required to generate chat answers.")

    from openai import OpenAI

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

    if not content:
        raise RagChatError("LLM returned an empty answer.")

    return content


def _snippet(content: str, max_length: int = 500) -> str:
    normalized = content.strip()
    return normalized[:max_length]


def _score_from_distance(distance: float | None) -> float | None:
    if distance is None:
        return None

    return 1 / (1 + distance)

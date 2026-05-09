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
    if language == "ko":
        if not search_results:
            return (
                "현재 저장된 코드 청크에서 관련 내용을 찾지 못했습니다. "
                "먼저 저장소 스캔과 코드 청크 생성을 실행한 뒤 다시 질문해 주세요."
            )

        lines = [
            "OpenAI API 키가 없어서 로컬 컨텍스트 기반으로만 답변합니다.",
            "찾은 관련 파일:",
        ]
        lines.extend(
            f"- {result['file_path']}:{result['start_line']}-{result['end_line']}" for result in search_results[:3]
        )
        lines.append("질문에 맞는 세부 설명이 필요하면 코드 청크와 임베딩 생성 후 다시 시도해 주세요.")
        return "\n".join(lines)

    if not search_results:
        return (
            "I couldn't find relevant content in the stored code chunks yet. "
            "Run repository scanning and chunk generation first, then ask again."
        )

    lines = [
        "OpenAI API key is not configured, so this answer is based only on local repository context.",
        "Relevant files found:",
    ]
    lines.extend(
        f"- {result['file_path']}:{result['start_line']}-{result['end_line']}" for result in search_results[:3]
    )
    lines.append("If you need a fuller answer, generate code chunks and embeddings first.")
    return "\n".join(lines)


def _snippet(content: str, max_length: int = 500) -> str:
    normalized = content.strip()
    return normalized[:max_length]


def _score_from_distance(distance: float | None) -> float | None:
    if distance is None:
        return None

    return 1 / (1 + distance)

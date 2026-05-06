from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat_schema import (
    ChatMessageRead,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionRead,
)
from app.schemas.project_schema import ApiResponse
from app.services.project_service import ProjectNotFoundError
from app.services.rag_chat_service import (
    RagChatError,
    answer_chat,
    create_chat_session,
    list_chat_messages,
    list_chat_sessions,
)


router = APIRouter(prefix="/projects", tags=["chat"])


@router.post("/{project_id}/chat/sessions", response_model=ApiResponse[ChatSessionRead])
def create_project_chat_session(
    project_id: str,
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[ChatSessionRead]:
    try:
        return ApiResponse(data=create_chat_session(db, project_id, payload))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session.",
        ) from exc


@router.get("/{project_id}/chat/sessions", response_model=ApiResponse[list[ChatSessionRead]])
def get_project_chat_sessions(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ChatSessionRead]]:
    try:
        return ApiResponse(data=list_chat_sessions(db, project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.get(
    "/{project_id}/chat/sessions/{session_id}/messages",
    response_model=ApiResponse[list[ChatMessageRead]],
)
def get_project_chat_messages(
    project_id: str,
    session_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ChatMessageRead]]:
    try:
        return ApiResponse(data=list_chat_messages(db, project_id, session_id))
    except RagChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{project_id}/chat", response_model=ApiResponse[ChatResponse])
def chat_with_project(
    project_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[ChatResponse]:
    try:
        session, user_message, assistant_message = answer_chat(db, project_id, payload)
        return ApiResponse(
            data=ChatResponse(
                session=session,
                user_message=user_message,
                assistant_message=assistant_message,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except RagChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save chat messages.",
        ) from exc

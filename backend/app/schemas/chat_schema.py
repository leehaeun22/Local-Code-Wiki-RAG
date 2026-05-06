from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=255)


class ChatSessionRead(BaseModel):
    id: str
    project_id: str
    user_id: str | None
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatReferenceRead(BaseModel):
    id: str
    file_id: str | None
    chunk_id: str | None
    document_id: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    snippet: str | None
    score: float | None
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    language: str
    references: list[ChatReferenceRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None
    language: Literal["ko", "en"] = "ko"
    top_k: int = Field(default=5, ge=1, le=10)


class ChatResponse(BaseModel):
    session: ChatSessionRead
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead

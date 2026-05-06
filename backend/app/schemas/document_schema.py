from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentType = Literal["overview", "folder_structure", "api_documentation", "onboarding_guide"]
DocumentLanguage = Literal["ko", "en"]


class DocumentGenerateRequest(BaseModel):
    language: DocumentLanguage = "ko"
    document_types: list[DocumentType] = Field(
        default_factory=lambda: [
            "overview",
            "folder_structure",
            "api_documentation",
            "onboarding_guide",
        ],
    )


class DocumentRead(BaseModel):
    id: str
    project_id: str
    file_id: str | None
    generated_from_commit_id: str | None
    generated_from_commit_hash: str | None
    document_type: str
    title: str
    content: str
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentGenerationResult(BaseModel):
    project_id: str
    generated_document_count: int
    documents: list[DocumentRead]


class DocumentTranslateRequest(BaseModel):
    target_language: DocumentLanguage
    preserve_terms: bool = True


class DocumentTranslationRead(BaseModel):
    id: str
    document_id: str
    language: str
    title: str
    content: str
    translation_status: str
    preserve_terms: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

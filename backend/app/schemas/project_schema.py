from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT
    message: str = "success"


class ProjectSettingRead(BaseModel):
    id: str
    default_language: str
    llm_mode: str
    llm_provider_id: str
    embedding_provider_id: str

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    repository_url: str = Field(min_length=1, max_length=500)
    branch: str = Field(default="main", min_length=1, max_length=100)
    description: str | None = None


class ProjectCreate(ProjectBase):
    default_language: str = Field(default="ko", min_length=2, max_length=10)
    llm_mode: str = Field(default="cloud", min_length=1, max_length=20)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    repository_url: str | None = Field(default=None, min_length=1, max_length=500)
    branch: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    default_language: str | None = Field(default=None, min_length=2, max_length=10)
    llm_mode: str | None = Field(default=None, min_length=1, max_length=20)


class ProjectRead(BaseModel):
    id: str
    owner_id: str
    name: str
    repository_url: str
    branch: str
    description: str | None
    local_path: str | None
    last_commit_hash: str | None
    settings: ProjectSettingRead | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteProjectResult(BaseModel):
    id: str


class ProjectCloneResult(BaseModel):
    project_id: str
    local_path: str
    commit_hash: str
    task_id: str


class AnalysisStatusRead(BaseModel):
    project_id: str
    file_count: int
    chunk_count: int
    document_count: int
    has_files: bool
    has_chunks: bool
    has_documents: bool

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RepositoryFileRead(BaseModel):
    id: str
    project_id: str
    file_path: str
    language: str | None
    content_hash: str | None
    size_bytes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepositoryScanResult(BaseModel):
    project_id: str
    scanned_file_count: int
    task_id: str


class FileTreeNode(BaseModel):
    name: str
    path: str
    type: Literal["directory", "file"]
    children: list["FileTreeNode"] = Field(default_factory=list)

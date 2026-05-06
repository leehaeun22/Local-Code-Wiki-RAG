from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CodeChunkRead(BaseModel):
    id: str
    project_id: str
    file_id: str
    chunk_index: int
    chunk_type: str
    start_line: int
    end_line: int
    content: str
    content_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CodeChunkGenerationResult(BaseModel):
    project_id: str
    generated_chunk_count: int
    task_id: str

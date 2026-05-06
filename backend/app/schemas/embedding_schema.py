from pydantic import BaseModel, Field


class EmbeddingGenerationResult(BaseModel):
    project_id: str
    embedded_chunk_count: int
    vector_collection_name: str
    task_id: str


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class VectorSearchResult(BaseModel):
    chunk_id: str
    file_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    distance: float | None = None
    metadata: dict

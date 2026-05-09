import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.embeddings.base_embedding import EmbeddingProvider
from app.ai.embeddings.openai_embedding import OpenAIEmbeddingProvider
from app.ai.vectorstores.base_vectorstore import VectorStore
from app.ai.vectorstores.chroma_vectorstore import ChromaVectorStore
from app.models.analysis_task import AnalysisTask
from app.models.code_chunk import CodeChunk
from app.services.project_service import ProjectNotFoundError, get_project


class EmbeddingGenerationError(Exception):
    pass


def _collection_name(project_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", project_id).lower()
    return f"project_{normalized}_code_chunks"


def _create_embedding_task(db: Session, project_id: str) -> AnalysisTask:
    task = AnalysisTask(
        project_id=project_id,
        commit_id=None,
        task_type="embedding",
        status="running",
        progress=0,
        error_message=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _list_chunks(db: Session, project_id: str) -> list[CodeChunk]:
    return list(
        db.scalars(
            select(CodeChunk)
            .options(selectinload(CodeChunk.file))
            .where(CodeChunk.project_id == project_id)
            .order_by(CodeChunk.file_id, CodeChunk.chunk_index),
        ).all(),
    )


def _chunk_metadata(chunk: CodeChunk) -> dict[str, Any]:
    return {
        "project_id": chunk.project_id,
        "file_id": chunk.file_id,
        "chunk_id": chunk.id,
        "file_path": chunk.file.file_path,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
    }


def _tokenize_query(query: str) -> list[str]:
    return [token for token in re.findall(r"\w+", query.lower(), flags=re.UNICODE) if len(token) > 1]


def _score_chunk_for_query(query: str, chunk: CodeChunk) -> float:
    tokens = _tokenize_query(query)

    if not tokens:
        return 0.0

    haystack = f"{chunk.file.file_path}\n{chunk.content}".lower()
    score = 0.0

    for token in tokens:
        if token in haystack:
            score += 1.0

    if query.lower() in haystack:
        score += 2.0

    return score


def _fallback_search_project_chunks(
    db: Session,
    project_id: str,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    chunks = _list_chunks(db, project_id)

    ranked_chunks = sorted(
        chunks,
        key=lambda chunk: (
            _score_chunk_for_query(query, chunk),
            chunk.created_at,
        ),
        reverse=True,
    )

    results: list[dict[str, Any]] = []

    for chunk in ranked_chunks[:top_k]:
        score = _score_chunk_for_query(query, chunk)

        if score <= 0:
            continue

        results.append(
            {
                "chunk_id": chunk.id,
                "file_id": chunk.file_id,
                "file_path": chunk.file.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
                "distance": 1 / (1 + score),
                "metadata": _chunk_metadata(chunk),
            },
        )

    return results


def generate_embeddings(
    db: Session,
    project_id: str,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
) -> tuple[int, str, AnalysisTask]:
    try:
        get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    task = _create_embedding_task(db, project_id)
    collection_name = _collection_name(project_id)

    try:
        chunks = _list_chunks(db, project_id)

        if not chunks:
            raise EmbeddingGenerationError("No code chunks found. Generate chunks first.")

        embedding_provider = embedding_provider or OpenAIEmbeddingProvider()
        vector_store = vector_store or ChromaVectorStore()
        texts = [chunk.content for chunk in chunks]
        embeddings = embedding_provider.embed_documents(texts)

        if len(embeddings) != len(chunks):
            raise EmbeddingGenerationError("Embedding provider returned an unexpected result count.")

        ids = [chunk.id for chunk in chunks]
        metadatas = [_chunk_metadata(chunk) for chunk in chunks]
        vector_store.upsert(
            collection_name=collection_name,
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        for chunk in chunks:
            chunk.embedding_id = chunk.id
            chunk.vector_collection_name = collection_name

        task.status = "completed"
        task.progress = 100
        task.error_message = None
        db.commit()
        db.refresh(task)

        return len(chunks), collection_name, task
    except Exception as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = str(exc)
            db.commit()

        if isinstance(exc, EmbeddingGenerationError):
            raise

        raise EmbeddingGenerationError(str(exc)) from exc


def search_project_chunks(
    db: Session,
    project_id: str,
    query: str,
    top_k: int,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
) -> list[dict[str, Any]]:
    try:
        get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    collection_name = _collection_name(project_id)

    try:
        embedding_provider = embedding_provider or OpenAIEmbeddingProvider()
        vector_store = vector_store or ChromaVectorStore()
        query_embedding = embedding_provider.embed_query(query)
        results = vector_store.search(collection_name, query_embedding, top_k)
        chunk_ids = [item["id"] for item in results]

        if not chunk_ids:
            return _fallback_search_project_chunks(db, project_id, query, top_k)

        chunks_by_id = {
            chunk.id: chunk
            for chunk in db.scalars(
                select(CodeChunk)
                .options(selectinload(CodeChunk.file))
                .where(CodeChunk.id.in_(chunk_ids)),
            ).all()
        }

        hydrated_results: list[dict[str, Any]] = []

        for item in results:
            chunk = chunks_by_id.get(item["id"])

            if chunk is None:
                continue

            metadata = item["metadata"] or {}
            hydrated_results.append(
                {
                    "chunk_id": chunk.id,
                    "file_id": chunk.file_id,
                    "file_path": chunk.file.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                    "distance": item.get("distance"),
                    "metadata": metadata,
                },
            )

        if hydrated_results:
            return hydrated_results
    except Exception:
        pass

    return _fallback_search_project_chunks(db, project_id, query, top_k)

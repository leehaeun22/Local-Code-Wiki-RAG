from pathlib import Path
import hashlib

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.chunkers.base import BaseChunker
from app.ai.chunkers.line_based import LineBasedChunker
from app.models.analysis_task import AnalysisTask
from app.models.code_chunk import CodeChunk
from app.models.repository_file import RepositoryFile
from app.services.project_service import ProjectNotFoundError, get_project


class CodeChunkGenerationError(Exception):
    pass


def _create_chunking_task(db: Session, project_id: str) -> AnalysisTask:
    task = AnalysisTask(
        project_id=project_id,
        commit_id=None,
        task_type="chunking",
        status="running",
        progress=0,
        error_message=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _read_file(root_path: Path, file_path: str) -> str:
    absolute_path = root_path / file_path

    if not absolute_path.exists() or not absolute_path.is_file():
        raise CodeChunkGenerationError(f"Repository file does not exist: {file_path}")

    return absolute_path.read_text(encoding="utf-8", errors="replace")


def generate_code_chunks(
    db: Session,
    project_id: str,
    chunker: BaseChunker | None = None,
) -> tuple[list[CodeChunk], AnalysisTask]:
    try:
        project = get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    task = _create_chunking_task(db, project_id)
    chunker = chunker or LineBasedChunker(chunk_size=120, overlap=20)

    try:
        if not project.local_path:
            raise CodeChunkGenerationError("Project local_path is empty. Clone the repository first.")

        root_path = Path(project.local_path)

        if not root_path.exists() or not root_path.is_dir():
            raise CodeChunkGenerationError(f"Project local_path does not exist: {project.local_path}")

        repository_files = list(
            db.scalars(
                select(RepositoryFile)
                .where(RepositoryFile.project_id == project_id)
                .order_by(RepositoryFile.file_path),
            ).all(),
        )

        if not repository_files:
            raise CodeChunkGenerationError("No repository files found. Scan the repository first.")

        db.execute(delete(CodeChunk).where(CodeChunk.project_id == project_id))
        generated_chunks: list[CodeChunk] = []

        for repository_file in repository_files:
            file_content = _read_file(root_path, repository_file.file_path)

            for chunk_index, chunk in enumerate(chunker.chunk(file_content)):
                code_chunk = CodeChunk(
                    project_id=project_id,
                    file_id=repository_file.id,
                    chunk_index=chunk_index,
                    chunk_type=chunk.chunk_type,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    content=chunk.content,
                    content_hash=_content_hash(chunk.content),
                )
                db.add(code_chunk)
                generated_chunks.append(code_chunk)

        task.status = "completed"
        task.progress = 100
        task.error_message = None
        db.commit()

        for code_chunk in generated_chunks:
            db.refresh(code_chunk)
        db.refresh(task)

        return generated_chunks, task
    except Exception as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = str(exc)
            db.commit()

        if isinstance(exc, CodeChunkGenerationError):
            raise

        raise CodeChunkGenerationError(str(exc)) from exc


def list_code_chunks(db: Session, project_id: str) -> list[CodeChunk]:
    get_project(db, project_id)
    return list(
        db.scalars(
            select(CodeChunk)
            .join(RepositoryFile, CodeChunk.file_id == RepositoryFile.id)
            .where(CodeChunk.project_id == project_id)
            .order_by(RepositoryFile.file_path, CodeChunk.chunk_index),
        ).all(),
    )

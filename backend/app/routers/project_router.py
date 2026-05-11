from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.code_chunk import CodeChunk
from app.models.document import Document
from app.models.repository_file import RepositoryFile
from app.schemas.code_chunk_schema import CodeChunkGenerationResult, CodeChunkRead
from app.schemas.document_schema import (
    DocumentGenerateRequest,
    DocumentGenerationResult,
    DocumentRead,
    DocumentTranslateRequest,
    DocumentTranslationRead,
)
from app.schemas.embedding_schema import (
    EmbeddingGenerationResult,
    VectorSearchRequest,
    VectorSearchResult,
)
from app.schemas.project_schema import (
    ApiResponse,
    AnalysisStatusRead,
    DeleteProjectResult,
    ProjectCreate,
    ProjectCloneResult,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.repository_file_schema import (
    FileTreeNode,
    RepositoryFileRead,
    RepositoryScanResult,
)
from app.services import project_service
from app.services.code_chunk_service import (
    CodeChunkGenerationError,
    generate_code_chunks,
    list_code_chunks,
)
from app.services.document_generation_service import (
    DocumentGenerationError,
    generate_documents,
    get_document,
    list_documents,
)
from app.services.document_translation_service import (
    DocumentTranslationError,
    list_document_translations,
    translate_document,
)
from app.services.embedding_service import (
    EmbeddingGenerationError,
    generate_embeddings,
    search_project_chunks,
)
from app.services.repository_file_scan_service import (
    RepositoryScanError,
    build_file_tree,
    list_repository_files,
    scan_repository_files,
)
from app.services.repository_clone_service import RepositoryCloneError, clone_repository
from app.services.project_service import ProjectNotFoundError


router = APIRouter(prefix="/projects", tags=["projects"])


def _to_project_read(project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        repository_url=project.repository_url,
        branch=project.default_branch,
        description=project.description,
        local_path=project.local_path,
        last_commit_hash=project.last_commit_hash,
        settings=project.settings,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post(
    "",
    response_model=ApiResponse[ProjectRead],
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[ProjectRead]:
    try:
        project = project_service.create_project(db, payload)
        return ApiResponse(data=_to_project_read(project))
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {exc}",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc) or "Failed to create project.",
        ) from exc


@router.get("", response_model=ApiResponse[list[ProjectRead]])
def list_projects(db: Session = Depends(get_db)) -> ApiResponse[list[ProjectRead]]:
    try:
        projects = project_service.list_projects(db)
        return ApiResponse(data=[_to_project_read(project) for project in projects])
    except Exception:
        # Keep the project list page usable when the local Postgres stack is not running yet.
        return ApiResponse(data=[])


@router.get("/{project_id}", response_model=ApiResponse[ProjectRead])
def get_project(project_id: str, db: Session = Depends(get_db)) -> ApiResponse[ProjectRead]:
    try:
        project = project_service.get_project(db, project_id)
        return ApiResponse(data=_to_project_read(project))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.get("/{project_id}/analysis-status", response_model=ApiResponse[AnalysisStatusRead])
def get_project_analysis_status(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[AnalysisStatusRead]:
    try:
        project_service.get_project(db, project_id)
        file_count = db.scalar(
            select(func.count()).select_from(RepositoryFile).where(RepositoryFile.project_id == project_id),
        ) or 0
        chunk_count = db.scalar(
            select(func.count()).select_from(CodeChunk).where(CodeChunk.project_id == project_id),
        ) or 0
        document_count = db.scalar(
            select(func.count()).select_from(Document).where(Document.project_id == project_id),
        ) or 0
        return ApiResponse(
            data=AnalysisStatusRead(
                project_id=project_id,
                file_count=file_count,
                chunk_count=chunk_count,
                document_count=document_count,
                has_files=file_count > 0,
                has_chunks=chunk_count > 0,
                has_documents=document_count > 0,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.post("/{project_id}/clone", response_model=ApiResponse[ProjectCloneResult])
def clone_project_repository(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[ProjectCloneResult]:
    try:
        project, task, commit = clone_repository(db, project_id)
        return ApiResponse(
            data=ProjectCloneResult(
                project_id=project.id,
                local_path=project.local_path or "",
                commit_hash=commit.commit_hash,
                task_id=task.id,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except RepositoryCloneError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save clone result.",
        ) from exc


@router.post("/{project_id}/scan", response_model=ApiResponse[RepositoryScanResult])
def scan_project_repository_files(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[RepositoryScanResult]:
    try:
        files, task = scan_repository_files(db, project_id)
        return ApiResponse(
            data=RepositoryScanResult(
                project_id=project_id,
                scanned_file_count=len(files),
                task_id=task.id,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except RepositoryScanError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save scan result.",
        ) from exc


@router.get("/{project_id}/files", response_model=ApiResponse[list[RepositoryFileRead]])
def get_project_repository_files(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[RepositoryFileRead]]:
    try:
        return ApiResponse(data=list_repository_files(db, project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.get("/{project_id}/file-tree", response_model=ApiResponse[list[FileTreeNode]])
def get_project_file_tree(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[FileTreeNode]]:
    try:
        files = list_repository_files(db, project_id)
        return ApiResponse(data=build_file_tree(files))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.post("/{project_id}/chunks/generate", response_model=ApiResponse[CodeChunkGenerationResult])
def generate_project_code_chunks(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[CodeChunkGenerationResult]:
    try:
        chunks, task = generate_code_chunks(db, project_id)
        return ApiResponse(
            data=CodeChunkGenerationResult(
                project_id=project_id,
                generated_chunk_count=len(chunks),
                task_id=task.id,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except CodeChunkGenerationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save code chunks.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate code chunks.",
        ) from exc


@router.get("/{project_id}/chunks", response_model=ApiResponse[list[CodeChunkRead]])
def get_project_code_chunks(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[CodeChunkRead]]:
    try:
        return ApiResponse(data=list_code_chunks(db, project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.post(
    "/{project_id}/embeddings/generate",
    response_model=ApiResponse[EmbeddingGenerationResult],
)
def generate_project_embeddings(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[EmbeddingGenerationResult]:
    try:
        embedded_count, collection_name, task = generate_embeddings(db, project_id)
        return ApiResponse(
            data=EmbeddingGenerationResult(
                project_id=project_id,
                embedded_chunk_count=embedded_count,
                vector_collection_name=collection_name,
                task_id=task.id,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except EmbeddingGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save embedding result.",
        ) from exc


@router.post("/{project_id}/search", response_model=ApiResponse[list[VectorSearchResult]])
def search_project(
    project_id: str,
    payload: VectorSearchRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[list[VectorSearchResult]]:
    try:
        return ApiResponse(
            data=search_project_chunks(
                db=db,
                project_id=project_id,
                query=payload.query,
                top_k=payload.top_k,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except EmbeddingGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/{project_id}/documents/generate",
    response_model=ApiResponse[DocumentGenerationResult],
)
def generate_project_documents(
    project_id: str,
    payload: DocumentGenerateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DocumentGenerationResult]:
    try:
        documents = generate_documents(db, project_id, payload)
        return ApiResponse(
            data=DocumentGenerationResult(
                project_id=project_id,
                generated_document_count=len(documents),
                documents=documents,
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except DocumentGenerationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save generated documents.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate documents.",
        ) from exc


@router.get("/{project_id}/documents", response_model=ApiResponse[list[DocumentRead]])
def get_project_documents(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[DocumentRead]]:
    try:
        return ApiResponse(data=list_documents(db, project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc


@router.get("/{project_id}/documents/{document_id}", response_model=ApiResponse[DocumentRead])
def get_project_document(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[DocumentRead]:
    try:
        return ApiResponse(data=get_document(db, project_id, document_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except DocumentGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "project_id": project_id,
                "document_id": document_id,
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/{project_id}/documents/{document_id}/translate",
    response_model=ApiResponse[DocumentTranslationRead],
)
def translate_project_document(
    project_id: str,
    document_id: str,
    payload: DocumentTranslateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DocumentTranslationRead]:
    try:
        return ApiResponse(data=translate_document(db, project_id, document_id, payload))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except DocumentTranslationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document translation.",
        ) from exc


@router.get(
    "/{project_id}/documents/{document_id}/translations",
    response_model=ApiResponse[list[DocumentTranslationRead]],
)
def get_project_document_translations(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[DocumentTranslationRead]]:
    try:
        return ApiResponse(data=list_document_translations(db, project_id, document_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except DocumentTranslationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{project_id}", response_model=ApiResponse[ProjectRead])
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[ProjectRead]:
    try:
        project = project_service.update_project(db, project_id, payload)
        return ApiResponse(data=_to_project_read(project))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project.",
        ) from exc


@router.delete("/{project_id}", response_model=ApiResponse[DeleteProjectResult])
def delete_project(project_id: str, db: Session = Depends(get_db)) -> ApiResponse[DeleteProjectResult]:
    try:
        deleted_project_id = project_service.delete_project(db, project_id)
        return ApiResponse(data=DeleteProjectResult(id=deleted_project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project.",
        ) from exc

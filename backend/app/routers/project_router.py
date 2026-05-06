from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.project_schema import (
    ApiResponse,
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
            detail="Failed to create project.",
        ) from exc


@router.get("", response_model=ApiResponse[list[ProjectRead]])
def list_projects(db: Session = Depends(get_db)) -> ApiResponse[list[ProjectRead]]:
    projects = project_service.list_projects(db)
    return ApiResponse(data=[_to_project_read(project) for project in projects])


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
    except RepositoryCloneError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone repository.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save clone result.",
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

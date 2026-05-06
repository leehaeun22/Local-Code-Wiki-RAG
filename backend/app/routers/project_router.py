from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.project_schema import (
    ApiResponse,
    DeleteProjectResult,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.services import project_service
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

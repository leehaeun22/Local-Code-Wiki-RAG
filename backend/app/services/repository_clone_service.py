from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Callable

from git import Repo
from git.exc import GitCommandError
from sqlalchemy.orm import Session

from app.models.analysis_task import AnalysisTask
from app.models.commit import Commit
from app.models.project import Project
from app.services.project_service import ProjectNotFoundError, get_project


class RepositoryCloneError(Exception):
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_STORAGE_ROOT = BACKEND_ROOT / "storage" / "repos"
logger = logging.getLogger(__name__)
REPOSITORY_URL_PATTERN = re.compile(r"^https://(github\.com|www\.github\.com)/.+/.+")


def _create_clone_task(db: Session, project_id: str) -> AnalysisTask:
    task = AnalysisTask(
        project_id=project_id,
        commit_id=None,
        task_type="clone",
        status="running",
        progress=0,
        error_message=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _extract_commit(repo: Repo, project: Project) -> Commit:
    head_commit = repo.head.commit
    author = head_commit.author
    committed_at = datetime.fromtimestamp(head_commit.committed_date, tz=timezone.utc)

    return Commit(
        project_id=project.id,
        commit_hash=head_commit.hexsha,
        branch=project.default_branch,
        author_name=author.name,
        author_email=author.email,
        message=head_commit.message.strip(),
        committed_at=committed_at,
    )


def _validate_repository_url(repository_url: str | None) -> str:
    normalized = (repository_url or "").strip()

    if not normalized:
        raise RepositoryCloneError(
            "Repository clone failed for URL ''. Repository URL is required.",
            status_code=400,
        )

    if not REPOSITORY_URL_PATTERN.match(normalized):
        raise RepositoryCloneError(
            (
                f"Repository clone failed for URL '{normalized}'. Invalid repository URL format. "
                "Check that the repository URL is public and valid."
            ),
            status_code=400,
        )

    return normalized


def _is_within_repository_storage(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPOSITORY_STORAGE_ROOT.resolve())
        return True
    except ValueError:
        return False


def _handle_remove_readonly(
    func: Callable[[str], None],
    path: str,
    exc_info,
) -> None:
    exc = exc_info[1]

    if isinstance(exc, PermissionError):
        os.chmod(path, stat.S_IWRITE)
        func(path)
        return

    raise exc


def _remove_existing_clone_path(clone_path: Path) -> None:
    if not clone_path.exists():
        return

    if not _is_within_repository_storage(clone_path):
        raise RepositoryCloneError(
            (
                f"Repository delete failed for path '{clone_path}'. Refusing to delete a path "
                "outside backend storage/repos."
            ),
        )

    try:
        shutil.rmtree(clone_path, onerror=_handle_remove_readonly)
    except Exception as exc:
        detail = (
            f"Repository delete failed for path '{clone_path}'. {exc}. "
            "Close any process using this repository and try again."
        )
        logger.exception(
            "Repository cleanup failed for clone_path=%s",
            clone_path,
        )
        raise RepositoryCloneError(detail) from exc

    if clone_path.exists():
        detail = (
            f"Repository delete failed for path '{clone_path}'. Directory still exists after cleanup. "
            "Close any process using this repository and try again."
        )
        logger.error(
            "Repository cleanup incomplete for clone_path=%s",
            clone_path,
        )
        raise RepositoryCloneError(detail)


def clone_repository(db: Session, project_id: str) -> tuple[Project, AnalysisTask, Commit]:
    try:
        project = get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    task = _create_clone_task(db, project_id)
    clone_path = REPOSITORY_STORAGE_ROOT / project_id

    try:
        repository_url = _validate_repository_url(project.repository_url)

        # TODO: Add access token based clone support for private GitHub repositories.
        _remove_existing_clone_path(clone_path)

        REPOSITORY_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

        repo = Repo.clone_from(
            repository_url,
            clone_path,
            branch=project.default_branch,
            single_branch=True,
        )

        commit = _extract_commit(repo, project)
        db.add(commit)
        db.flush()

        project.local_path = str(clone_path)
        project.last_commit_hash = commit.commit_hash
        task.commit_id = commit.id
        task.status = "completed"
        task.progress = 100
        task.error_message = None

        db.commit()
        db.refresh(project)
        db.refresh(task)
        db.refresh(commit)

        return project, task, commit
    except RepositoryCloneError as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = exc.detail
            db.commit()

        logger.warning(
            "Repository clone validation failed for project_id=%s repository_url=%s: %s",
            project_id,
            project.repository_url,
            exc.detail,
        )
        raise
    except GitCommandError as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)
        detail = (
            f"Repository clone failed for URL '{project.repository_url}'. {exc}. "
            "Check that the repository URL is public and valid."
        )

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = detail
            db.commit()

        logger.exception(
            "Repository clone failed for project_id=%s repository_url=%s clone_path=%s",
            project_id,
            project.repository_url,
            clone_path,
        )
        raise RepositoryCloneError(detail) from exc
    except OSError as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)
        detail = (
            f"Repository clone failed for URL '{project.repository_url}'. {exc}. "
            "Check that the repository URL is public and valid."
        )

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = detail
            db.commit()

        logger.exception(
            "Repository clone OS failure for project_id=%s repository_url=%s clone_path=%s",
            project_id,
            project.repository_url,
            clone_path,
        )
        raise RepositoryCloneError(detail) from exc
    except Exception as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)
        detail = (
            f"Repository clone failed for URL '{project.repository_url}'. Unexpected error: {exc}. "
            "Check that the repository URL is public and valid."
        )

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = detail
            db.commit()

        logger.exception(
            "Unexpected repository clone failure for project_id=%s repository_url=%s clone_path=%s",
            project_id,
            project.repository_url,
            clone_path,
        )
        raise RepositoryCloneError(detail) from exc

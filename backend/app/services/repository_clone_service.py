from datetime import datetime, timezone
from pathlib import Path
import shutil

from git import Repo
from git.exc import GitCommandError
from sqlalchemy.orm import Session

from app.models.analysis_task import AnalysisTask
from app.models.commit import Commit
from app.models.project import Project
from app.services.project_service import ProjectNotFoundError, get_project


class RepositoryCloneError(Exception):
    pass


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_STORAGE_ROOT = BACKEND_ROOT / "storage" / "repos"


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


def clone_repository(db: Session, project_id: str) -> tuple[Project, AnalysisTask, Commit]:
    try:
        project = get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    task = _create_clone_task(db, project_id)
    clone_path = REPOSITORY_STORAGE_ROOT / project_id

    try:
        # TODO: Add access token based clone support for private GitHub repositories.
        if clone_path.exists():
            shutil.rmtree(clone_path)

        REPOSITORY_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

        repo = Repo.clone_from(
            project.repository_url,
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
    except (GitCommandError, OSError) as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = str(exc)
            db.commit()

        raise RepositoryCloneError(str(exc)) from exc

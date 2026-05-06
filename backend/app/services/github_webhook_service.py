from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_task import AnalysisTask
from app.models.commit import Commit
from app.models.file_change import FileChange
from app.models.project import Project
from app.models.repository_file import RepositoryFile
from app.models.webhook_event import WebhookEvent


class GitHubWebhookError(Exception):
    pass


def process_github_push(
    db: Session,
    payload: dict,
    delivery_id: str | None,
) -> tuple[bool, str | None, Project | None, Commit | None, AnalysisTask | None]:
    repository = payload.get("repository") or {}
    project = _find_project(db, repository)

    if project is None:
        return False, "Project not found.", None, None, None

    push_branch = _extract_branch(payload.get("ref", ""))

    if push_branch != project.default_branch:
        return False, "Push branch does not match project branch.", project, None, None

    head_commit = payload.get("head_commit")

    if not head_commit:
        return False, "head_commit is missing.", project, None, None

    commit = _create_commit(db, project, push_branch, head_commit)
    webhook_event = WebhookEvent(
        project_id=project.id,
        commit_id=commit.id,
        provider="github",
        event_type="push",
        delivery_id=delivery_id,
        payload=payload,
    )
    db.add(webhook_event)
    _create_file_changes(db, project, commit, head_commit)
    task = AnalysisTask(
        project_id=project.id,
        commit_id=commit.id,
        task_type="reanalysis",
        status="pending",
        progress=0,
        error_message=None,
    )
    db.add(task)
    project.last_commit_hash = commit.commit_hash

    # TODO: Trigger automatic clone, scan, chunking, embedding, and document regeneration pipeline.
    db.commit()
    db.refresh(commit)
    db.refresh(task)
    db.refresh(project)

    return True, None, project, commit, task


def _find_project(db: Session, repository: dict) -> Project | None:
    clone_url = repository.get("clone_url")
    html_url = repository.get("html_url")
    full_name = repository.get("full_name")
    candidates = [url for url in [clone_url, html_url] if url]

    if full_name:
        candidates.extend(
            [
                f"https://github.com/{full_name}",
                f"https://github.com/{full_name}.git",
            ],
        )

    normalized_candidates = {_normalize_repo_url(url) for url in candidates}

    projects = db.scalars(select(Project)).all()

    for project in projects:
        if _normalize_repo_url(project.repository_url) in normalized_candidates:
            return project

    if full_name:
        return db.scalar(select(Project).where(Project.repository_url.contains(full_name)))

    return None


def _normalize_repo_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").removesuffix(".git")
    return f"github.com/{path}".lower()


def _extract_branch(ref: str) -> str:
    prefix = "refs/heads/"
    return ref.removeprefix(prefix)


def _create_commit(db: Session, project: Project, branch: str, head_commit: dict) -> Commit:
    commit_hash = head_commit.get("id")
    author = head_commit.get("author") or {}

    if not commit_hash:
        raise GitHubWebhookError("head_commit.id is missing.")

    existing_commit = db.scalar(
        select(Commit).where(
            Commit.project_id == project.id,
            Commit.commit_hash == commit_hash,
        ),
    )

    if existing_commit is not None:
        return existing_commit

    commit = Commit(
        project_id=project.id,
        commit_hash=commit_hash,
        branch=branch,
        author_name=author.get("name"),
        author_email=author.get("email"),
        message=head_commit.get("message"),
        committed_at=_parse_datetime(head_commit.get("timestamp")),
    )
    db.add(commit)
    db.flush()
    return commit


def _create_file_changes(db: Session, project: Project, commit: Commit, head_commit: dict) -> None:
    for change_type, paths in [
        ("added", head_commit.get("added") or []),
        ("modified", head_commit.get("modified") or []),
        ("removed", head_commit.get("removed") or []),
    ]:
        for file_path in paths:
            repository_file = db.scalar(
                select(RepositoryFile).where(
                    RepositoryFile.project_id == project.id,
                    RepositoryFile.file_path == file_path,
                ),
            )
            file_change = FileChange(
                file_id=repository_file.id if repository_file else None,
                commit_id=commit.id,
                change_type=change_type,
                file_path=file_path,
                previous_file_path=None,
                previous_hash=None,
                current_hash=None,
            )
            db.add(file_change)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))

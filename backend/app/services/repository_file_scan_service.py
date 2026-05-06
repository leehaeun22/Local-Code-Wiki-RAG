from pathlib import Path
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_task import AnalysisTask
from app.models.repository_file import RepositoryFile
from app.schemas.repository_file_schema import FileTreeNode
from app.services.project_service import ProjectNotFoundError, get_project


class RepositoryScanError(Exception):
    pass


EXCLUDED_NAMES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".env",
    ".venv",
    "__pycache__",
}
SUPPORTED_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".java",
    ".md",
    ".json",
    ".yml",
    ".yaml",
}
LANGUAGE_BY_EXTENSION = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".java": "java",
    ".md": "markdown",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
}


def _create_scan_task(db: Session, project_id: str) -> AnalysisTask:
    task = AnalysisTask(
        project_id=project_id,
        commit_id=None,
        task_type="scan",
        status="running",
        progress=0,
        error_message=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in path.parts)


def _is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _content_hash(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def _scan_files(root_path: Path) -> list[Path]:
    files: list[Path] = []

    for path in root_path.rglob("*"):
        relative_path = path.relative_to(root_path)

        if _is_excluded(relative_path):
            continue

        if path.is_file() and _is_supported_file(path):
            files.append(path)

    return sorted(files)


def scan_repository_files(db: Session, project_id: str) -> tuple[list[RepositoryFile], AnalysisTask]:
    try:
        project = get_project(db, project_id)
    except ProjectNotFoundError:
        raise

    task = _create_scan_task(db, project_id)

    try:
        if not project.local_path:
            raise RepositoryScanError("Project local_path is empty. Clone the repository first.")

        root_path = Path(project.local_path)

        if not root_path.exists() or not root_path.is_dir():
            raise RepositoryScanError(f"Project local_path does not exist: {project.local_path}")

        existing_files = {
            file.file_path: file
            for file in db.scalars(
                select(RepositoryFile).where(RepositoryFile.project_id == project_id),
            ).all()
        }
        scanned_files: list[RepositoryFile] = []

        for path in _scan_files(root_path):
            relative_path = path.relative_to(root_path).as_posix()
            digest = _content_hash(path)
            repository_file = existing_files.get(relative_path)

            if repository_file is None:
                repository_file = RepositoryFile(
                    project_id=project_id,
                    file_path=relative_path,
                    language=LANGUAGE_BY_EXTENSION.get(path.suffix.lower()),
                    file_hash=digest,
                    content_hash=digest,
                    size_bytes=path.stat().st_size,
                )
                db.add(repository_file)
            else:
                repository_file.language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
                repository_file.file_hash = digest
                repository_file.content_hash = digest
                repository_file.size_bytes = path.stat().st_size

            scanned_files.append(repository_file)

        task.status = "completed"
        task.progress = 100
        task.error_message = None

        db.commit()

        for repository_file in scanned_files:
            db.refresh(repository_file)
        db.refresh(task)

        return scanned_files, task
    except Exception as exc:
        db.rollback()
        task = db.get(AnalysisTask, task.id)

        if task is not None:
            task.status = "failed"
            task.progress = 0
            task.error_message = str(exc)
            db.commit()

        if isinstance(exc, RepositoryScanError):
            raise

        raise RepositoryScanError(str(exc)) from exc


def list_repository_files(db: Session, project_id: str) -> list[RepositoryFile]:
    get_project(db, project_id)
    return list(
        db.scalars(
            select(RepositoryFile)
            .where(RepositoryFile.project_id == project_id)
            .order_by(RepositoryFile.file_path),
        ).all(),
    )


def build_file_tree(files: list[RepositoryFile]) -> list[FileTreeNode]:
    root: dict[str, dict] = {}

    for repository_file in files:
        current = root
        parts = repository_file.file_path.split("/")

        for index, part in enumerate(parts):
            node_path = "/".join(parts[: index + 1])
            is_file = index == len(parts) - 1

            current.setdefault(
                part,
                {
                    "name": part,
                    "path": node_path,
                    "type": "file" if is_file else "directory",
                    "children": {},
                },
            )
            current = current[part]["children"]

    return _tree_dict_to_nodes(root)


def _tree_dict_to_nodes(tree: dict[str, dict]) -> list[FileTreeNode]:
    nodes: list[FileTreeNode] = []

    for key in sorted(tree):
        value = tree[key]
        nodes.append(
            FileTreeNode(
                name=value["name"],
                path=value["path"],
                type=value["type"],
                children=_tree_dict_to_nodes(value["children"]),
            ),
        )

    return nodes

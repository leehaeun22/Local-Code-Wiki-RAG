from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.embedding_provider import EmbeddingProvider
from app.models.llm_provider import LLMProvider
from app.models.project import Project
from app.models.project_setting import ProjectSetting
from app.models.user import User
from app.schemas.project_schema import ProjectCreate, ProjectUpdate


class ProjectNotFoundError(Exception):
    pass


DEFAULT_USER_EMAIL = "system@local-code-wiki-rag.dev"
DEFAULT_USER_NAME = "System"
DEFAULT_LLM_PROVIDER_NAME = "default-cloud-llm"
DEFAULT_EMBEDDING_PROVIDER_NAME = "default-cloud-embedding"


def _get_or_create_system_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == DEFAULT_USER_EMAIL))

    if user is not None:
        return user

    user = User(email=DEFAULT_USER_EMAIL, name=DEFAULT_USER_NAME)
    db.add(user)
    db.flush()
    return user


def _get_or_create_default_llm_provider(db: Session) -> LLMProvider:
    provider = db.scalar(select(LLMProvider).where(LLMProvider.name == DEFAULT_LLM_PROVIDER_NAME))

    if provider is not None:
        return provider

    provider = LLMProvider(
        name=DEFAULT_LLM_PROVIDER_NAME,
        provider_type="cloud",
        model_name="gpt-4o-mini",
    )
    db.add(provider)
    db.flush()
    return provider


def _get_or_create_default_embedding_provider(db: Session) -> EmbeddingProvider:
    provider = db.scalar(
        select(EmbeddingProvider).where(EmbeddingProvider.name == DEFAULT_EMBEDDING_PROVIDER_NAME),
    )

    if provider is not None:
        return provider

    provider = EmbeddingProvider(
        name=DEFAULT_EMBEDDING_PROVIDER_NAME,
        provider_type="cloud",
        model_name="text-embedding-3-small",
        dimension=1536,
    )
    db.add(provider)
    db.flush()
    return provider


def _project_query():
    return select(Project).options(selectinload(Project.settings))


def create_project(db: Session, payload: ProjectCreate) -> Project:
    owner = _get_or_create_system_user(db)
    llm_provider = _get_or_create_default_llm_provider(db)
    embedding_provider = _get_or_create_default_embedding_provider(db)

    project = Project(
        owner_id=owner.id,
        name=payload.name,
        repository_url=payload.repository_url,
        default_branch=payload.branch,
        description=payload.description,
    )
    db.add(project)
    db.flush()

    project_settings = ProjectSetting(
        project_id=project.id,
        llm_provider_id=llm_provider.id,
        embedding_provider_id=embedding_provider.id,
        default_language=payload.default_language,
        llm_mode=payload.llm_mode,
    )
    db.add(project_settings)
    db.commit()

    return get_project(db, project.id)


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(_project_query().order_by(Project.created_at.desc())).all())


def get_project(db: Session, project_id: str) -> Project:
    project = db.scalar(_project_query().where(Project.id == project_id))

    if project is None:
        raise ProjectNotFoundError(project_id)

    return project


def update_project(db: Session, project_id: str, payload: ProjectUpdate) -> Project:
    project = get_project(db, project_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        project.name = update_data["name"]
    if "repository_url" in update_data:
        project.repository_url = update_data["repository_url"]
    if "branch" in update_data:
        project.default_branch = update_data["branch"]
    if "description" in update_data:
        project.description = update_data["description"]

    if project.settings is not None:
        if "default_language" in update_data:
            project.settings.default_language = update_data["default_language"]
        if "llm_mode" in update_data:
            project.settings.llm_mode = update_data["llm_mode"]

    db.commit()
    return get_project(db, project_id)


def delete_project(db: Session, project_id: str) -> str:
    project = get_project(db, project_id)

    if project.settings is not None:
        db.delete(project.settings)

    db.delete(project)
    db.commit()

    return project_id

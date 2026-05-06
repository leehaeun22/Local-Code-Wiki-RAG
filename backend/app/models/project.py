from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class Project(UUIDTimestampMixin, Base):
    __tablename__ = "projects"

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    repository_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_commit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="projects")
    settings: Mapped["ProjectSetting"] = relationship(back_populates="project", uselist=False)
    commits: Mapped[list["Commit"]] = relationship(back_populates="project")
    repository_files: Mapped[list["RepositoryFile"]] = relationship(back_populates="project")
    documents: Mapped[list["Document"]] = relationship(back_populates="project")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="project")
    analysis_tasks: Mapped[list["AnalysisTask"]] = relationship(back_populates="project")
    webhook_events: Mapped[list["WebhookEvent"]] = relationship(back_populates="project")

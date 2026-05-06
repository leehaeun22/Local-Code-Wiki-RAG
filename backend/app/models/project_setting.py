from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class ProjectSetting(UUIDTimestampMixin, Base):
    __tablename__ = "project_settings"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    llm_provider_id: Mapped[str] = mapped_column(ForeignKey("llm_providers.id"), nullable=False)
    embedding_provider_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_providers.id"),
        nullable=False,
    )
    default_language: Mapped[str] = mapped_column(String(10), default="ko", nullable=False)
    llm_mode: Mapped[str] = mapped_column(String(20), default="cloud", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="settings")
    llm_provider: Mapped["LLMProvider"] = relationship(back_populates="project_settings")
    embedding_provider: Mapped["EmbeddingProvider"] = relationship(
        back_populates="project_settings",
    )

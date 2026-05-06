from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class Document(UUIDTimestampMixin, Base):
    __tablename__ = "documents"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("repository_files.id"), nullable=False)
    generated_from_commit_id: Mapped[str | None] = mapped_column(
        ForeignKey("commits.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="ko", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="documents")
    file: Mapped["RepositoryFile"] = relationship(back_populates="documents")
    generated_from_commit: Mapped["Commit | None"] = relationship(back_populates="documents")
    translations: Mapped[list["DocumentTranslation"]] = relationship(back_populates="document")
    message_references: Mapped[list["MessageReference"]] = relationship(back_populates="document")

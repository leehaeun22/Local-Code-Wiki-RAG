from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class RepositoryFile(UUIDTimestampMixin, Base):
    __tablename__ = "repository_files"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="repository_files")
    code_chunks: Mapped[list["CodeChunk"]] = relationship(back_populates="file")
    documents: Mapped[list["Document"]] = relationship(back_populates="file")
    message_references: Mapped[list["MessageReference"]] = relationship(back_populates="file")
    file_changes: Mapped[list["FileChange"]] = relationship(back_populates="file")

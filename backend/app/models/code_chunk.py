from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class CodeChunk(UUIDTimestampMixin, Base):
    __tablename__ = "code_chunks"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("repository_files.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(50), default="line", nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vector_collection_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    file: Mapped["RepositoryFile"] = relationship(back_populates="code_chunks")
    message_references: Mapped[list["MessageReference"]] = relationship(back_populates="chunk")

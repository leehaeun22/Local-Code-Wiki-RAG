from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class MessageReference(UUIDTimestampMixin, Base):
    __tablename__ = "message_references"

    message_id: Mapped[str] = mapped_column(ForeignKey("chat_messages.id"), nullable=False)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("repository_files.id"), nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("code_chunks.id"), nullable=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    message: Mapped["ChatMessage"] = relationship(back_populates="references")
    file: Mapped["RepositoryFile | None"] = relationship(back_populates="message_references")
    chunk: Mapped["CodeChunk | None"] = relationship(back_populates="message_references")
    document: Mapped["Document | None"] = relationship(back_populates="message_references")

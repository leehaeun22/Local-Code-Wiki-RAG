from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class Commit(UUIDTimestampMixin, Base):
    __tablename__ = "commits"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    branch: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="commits")
    documents: Mapped[list["Document"]] = relationship(back_populates="generated_from_commit")
    analysis_tasks: Mapped[list["AnalysisTask"]] = relationship(back_populates="commit")
    webhook_events: Mapped[list["WebhookEvent"]] = relationship(back_populates="commit")
    file_changes: Mapped[list["FileChange"]] = relationship(back_populates="commit")

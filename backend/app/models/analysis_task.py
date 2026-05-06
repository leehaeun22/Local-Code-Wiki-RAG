from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class AnalysisTask(UUIDTimestampMixin, Base):
    __tablename__ = "analysis_tasks"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    commit_id: Mapped[str | None] = mapped_column(ForeignKey("commits.id"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="analysis_tasks")
    commit: Mapped["Commit | None"] = relationship(back_populates="analysis_tasks")

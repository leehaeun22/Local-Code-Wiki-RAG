from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class FileChange(UUIDTimestampMixin, Base):
    __tablename__ = "file_changes"

    file_id: Mapped[str | None] = mapped_column(ForeignKey("repository_files.id"), nullable=True)
    commit_id: Mapped[str | None] = mapped_column(ForeignKey("commits.id"), nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    previous_file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    file: Mapped["RepositoryFile"] = relationship(back_populates="file_changes")
    commit: Mapped["Commit | None"] = relationship(back_populates="file_changes")

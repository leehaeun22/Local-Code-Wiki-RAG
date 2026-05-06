from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class WebhookEvent(UUIDTimestampMixin, Base):
    __tablename__ = "webhook_events"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    commit_id: Mapped[str | None] = mapped_column(ForeignKey("commits.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="webhook_events")
    commit: Mapped["Commit | None"] = relationship(back_populates="webhook_events")

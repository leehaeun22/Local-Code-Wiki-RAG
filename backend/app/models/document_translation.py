from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDTimestampMixin


class DocumentTranslation(UUIDTimestampMixin, Base):
    __tablename__ = "document_translations"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    translation_status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    preserve_terms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="translations")

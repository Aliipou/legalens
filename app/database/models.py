"""Database models for analysis history storage."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class AnalysisRecord(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_created_at", "created_at"),
        Index("ix_analyses_overall_risk", "overall_risk"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    old_document_hash: Mapped[str] = mapped_column(String(64))
    new_document_hash: Mapped[str] = mapped_column(String(64))
    total_clauses_old: Mapped[int] = mapped_column(Integer)
    total_clauses_new: Mapped[int] = mapped_column(Integer)
    added: Mapped[int] = mapped_column(Integer)
    removed: Mapped[int] = mapped_column(Integer)
    modified: Mapped[int] = mapped_column(Integer)
    overall_risk: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(100), default="all-MiniLM-L6-v2")
    processing_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

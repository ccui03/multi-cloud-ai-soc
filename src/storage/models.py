"""SQLAlchemy models for collected WAF evidence and ingestion checkpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class StoredWAFRecord(Base):
    """A deduplicated copy of a source log record selected for local analysis."""

    __tablename__ = "waf_records"
    __table_args__ = (
        Index("ix_waf_records_source_event_time", "source_id", "event_time"),
        Index("ix_waf_records_provider_event_time", "provider", "event_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IngestionCheckpoint(Base):
    """Last fully completed query-window boundary for one configured source."""

    __tablename__ = "ingestion_checkpoints"

    source_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    watermark_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_success_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

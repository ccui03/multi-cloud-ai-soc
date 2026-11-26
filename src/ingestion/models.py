"""Shared data contracts for cloud log adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class QueryRequest:
    source_id: str
    start_time: datetime
    end_time: datetime
    filters: dict[str, Any] = field(default_factory=dict)
    page_size: int = 200
    cursor: str | None = None
    query_mode: str = "incremental"
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id is required")
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("start_time and end_time must be timezone-aware")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time")
        if not 1 <= self.page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")


@dataclass
class RawWAFRecord:
    provider: str
    source_id: str
    event_time: datetime | None
    raw: dict[str, Any]
    source_record_id: str | None = None
    fingerprint: str | None = None


@dataclass
class FetchPage:
    records: list[RawWAFRecord]
    next_cursor: str | None
    has_more: bool
    source_id: str
    request_id: str
    query_start: datetime
    query_end: datetime
    provider_request_id: str | None = None


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc)

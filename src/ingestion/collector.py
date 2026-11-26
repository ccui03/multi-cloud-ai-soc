"""Bounded incremental collection with overlap, pagination and checkpoint safety."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Any

from .models import QueryRequest, ensure_utc


@dataclass(frozen=True)
class CollectionResult:
    source_id: str
    records_seen: int
    records_inserted: int
    pages_fetched: int
    query_start: datetime
    query_end: datetime
    checkpoint_advanced: bool
    stopped_by_record_limit: bool = False


class IncrementalCollector:
    """Collect one bounded window and advance the watermark only after all pages finish."""

    def __init__(
        self,
        *,
        repository: Any,
        interval_seconds: int = 300,
        overlap_seconds: int = 120,
        initial_lookback_seconds: int = 900,
        safety_lag_seconds: int = 60,
        page_size: int = 100,
        max_records_per_run: int = 5000,
    ) -> None:
        if min(interval_seconds, initial_lookback_seconds, page_size, max_records_per_run) <= 0:
            raise ValueError("interval, initial lookback, page size and record limit must be positive")
        if overlap_seconds < 0 or safety_lag_seconds < 0:
            raise ValueError("overlap and safety lag cannot be negative")
        self.repository = repository
        self.interval_seconds = interval_seconds
        self.overlap_seconds = overlap_seconds
        self.initial_lookback_seconds = initial_lookback_seconds
        self.safety_lag_seconds = safety_lag_seconds
        self.page_size = min(page_size, 1000)
        self.max_records_per_run = max_records_per_run

    def collect(
        self,
        *,
        adapter: Any,
        provider: str,
        source_id: str,
        filters: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> CollectionResult:
        current = ensure_utc(now or datetime.now(timezone.utc))
        query_end = current - timedelta(seconds=self.safety_lag_seconds)
        checkpoint = self.repository.get_checkpoint(source_id)
        if checkpoint is None:
            query_start = query_end - timedelta(seconds=self.initial_lookback_seconds)
        else:
            query_start = ensure_utc(checkpoint.watermark_time) - timedelta(seconds=self.overlap_seconds)
        if query_start >= query_end:
            raise ValueError("Calculated ingestion window is empty or reversed")

        request_id = str(uuid4())
        cursor = None
        records_seen = 0
        records_inserted = 0
        pages_fetched = 0
        while True:
            request = QueryRequest(
                source_id=source_id,
                start_time=query_start,
                end_time=query_end,
                filters=filters or {},
                page_size=self.page_size,
                cursor=cursor,
                query_mode="incremental",
                request_id=request_id,
            )
            page = adapter.fetch_page(request)
            pages_fetched += 1
            records_seen += len(page.records)

            remaining = self.max_records_per_run - (records_seen - len(page.records))
            selected_records = page.records[:max(remaining, 0)]
            records_inserted += self.repository.save_records(selected_records)

            if len(page.records) > len(selected_records) or (page.has_more and records_seen >= self.max_records_per_run):
                return CollectionResult(
                    source_id, records_seen, records_inserted, pages_fetched,
                    query_start, query_end, False, True,
                )
            if not page.has_more:
                self.repository.advance_checkpoint(
                    source_id=source_id,
                    provider=provider,
                    watermark_time=query_end,
                    request_id=request_id,
                    completed_at=current,
                )
                return CollectionResult(
                    source_id, records_seen, records_inserted, pages_fetched,
                    query_start, query_end, True, False,
                )
            if not page.next_cursor:
                raise RuntimeError("Adapter reported has_more=True without a next_cursor; checkpoint was not advanced")
            cursor = page.next_cursor

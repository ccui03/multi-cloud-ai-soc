"""Idempotent persistence operations for WAF records and checkpoints."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker

from src.ingestion.models import RawWAFRecord, ensure_utc
from .models import IngestionCheckpoint, StoredWAFRecord


def build_fingerprint(record: RawWAFRecord) -> str:
    """Build a stable idempotency key without relying on mutable provider pagination."""
    if record.source_record_id:
        identity = {
            "provider": record.provider,
            "source_id": record.source_id,
            "source_record_id": record.source_record_id,
        }
    else:
        identity = {
            "provider": record.provider,
            "source_id": record.source_id,
            "event_time": ensure_utc(record.event_time).isoformat() if record.event_time else None,
            "raw": record.raw,
        }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class StorageRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def get_checkpoint(self, source_id: str) -> IngestionCheckpoint | None:
        with self.session_factory() as session:
            return session.get(IngestionCheckpoint, source_id)

    def save_records(self, records: Iterable[RawWAFRecord]) -> int:
        """Insert a page; duplicate fingerprints are ignored. Returns inserted row count."""
        rows = []
        for record in records:
            fingerprint = record.fingerprint or build_fingerprint(record)
            record.fingerprint = fingerprint
            rows.append({
                "provider": record.provider,
                "source_id": record.source_id,
                "event_time": ensure_utc(record.event_time) if record.event_time else None,
                "source_record_id": record.source_record_id,
                "fingerprint": fingerprint,
                "raw": record.raw,
            })
        if not rows:
            return 0

        dialect = self.session_factory.kw["bind"].dialect.name
        with self.session_factory.begin() as session:
            if dialect == "postgresql":
                statement = pg_insert(StoredWAFRecord).values(rows).on_conflict_do_nothing(
                    index_elements=["fingerprint"]
                )
            elif dialect == "sqlite":
                statement = sqlite_insert(StoredWAFRecord).values(rows).on_conflict_do_nothing(
                    index_elements=["fingerprint"]
                )
            else:
                raise RuntimeError(f"Unsupported database dialect for idempotent insert: {dialect}")
            result = session.execute(statement)
            return max(result.rowcount or 0, 0)

    def advance_checkpoint(
        self,
        *,
        source_id: str,
        provider: str,
        watermark_time: datetime,
        request_id: str | None,
        completed_at: datetime | None = None,
    ) -> None:
        watermark = ensure_utc(watermark_time)
        now = ensure_utc(completed_at or datetime.now(timezone.utc))
        with self.session_factory.begin() as session:
            checkpoint = session.get(IngestionCheckpoint, source_id)
            if checkpoint is None:
                session.add(IngestionCheckpoint(
                    source_id=source_id,
                    provider=provider,
                    watermark_time=watermark,
                    last_success_at=now,
                    last_request_id=request_id,
                ))
            else:
                checkpoint.provider = provider
                checkpoint.watermark_time = watermark
                checkpoint.last_success_at = now
                checkpoint.last_request_id = request_id

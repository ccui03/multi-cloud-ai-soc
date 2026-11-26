from datetime import datetime, timedelta, timezone

from src.ingestion.collector import IncrementalCollector
from src.ingestion.models import FetchPage, RawWAFRecord
from src.storage.database import Database
from src.storage.repository import StorageRepository


class FakeAdapter:
    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []

    def fetch_page(self, request):
        self.requests.append(request)
        return self.pages.pop(0)


def record(event_id: str, when: datetime):
    return RawWAFRecord(
        provider="aliyun",
        source_id="aliyun:test-project:test-logstore",
        event_time=when,
        raw={"event_id": event_id, "action": "block"},
        source_record_id=event_id,
    )


def make_page(records, *, has_more=False, cursor=None):
    now = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
    return FetchPage(
        records=records,
        next_cursor=cursor,
        has_more=has_more,
        source_id="aliyun:test-project:test-logstore",
        request_id="test-request",
        query_start=now - timedelta(minutes=10),
        query_end=now,
    )


def test_repository_deduplicates_records_and_persists_checkpoint():
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_schema()
    repository = StorageRepository(database.session_factory)
    now = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
    item = record("log-1", now)

    assert repository.save_records([item]) == 1
    assert repository.save_records([item]) == 0

    repository.advance_checkpoint(
        source_id=item.source_id,
        provider="aliyun",
        watermark_time=now,
        request_id="request-1",
        completed_at=now,
    )
    checkpoint = repository.get_checkpoint(item.source_id)
    assert checkpoint is not None
    assert checkpoint.watermark_time.replace(tzinfo=timezone.utc) == now
    database.close()


def test_collector_advances_checkpoint_only_after_all_pages():
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_schema()
    repository = StorageRepository(database.session_factory)
    source_id = "aliyun:test-project:test-logstore"
    now = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
    adapter = FakeAdapter([
        make_page([record("log-1", now)], has_more=True, cursor="page-2"),
        make_page([record("log-2", now)], has_more=False),
    ])
    collector = IncrementalCollector(repository=repository, initial_lookback_seconds=600)

    result = collector.collect(
        adapter=adapter,
        provider="aliyun",
        source_id=source_id,
        now=now,
    )

    assert result.checkpoint_advanced is True
    assert result.pages_fetched == 2
    assert result.records_seen == 2
    assert result.records_inserted == 2
    assert repository.get_checkpoint(source_id) is not None
    assert adapter.requests[0].cursor is None
    assert adapter.requests[1].cursor == "page-2"
    database.close()


def test_collector_does_not_advance_checkpoint_when_page_fails():
    database = Database("sqlite+pysqlite:///:memory:")
    database.create_schema()
    repository = StorageRepository(database.session_factory)
    source_id = "aliyun:test-project:test-logstore"
    now = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)

    class FailingAdapter:
        def fetch_page(self, request):
            raise RuntimeError("simulated provider failure")

    collector = IncrementalCollector(repository=repository, initial_lookback_seconds=600)
    try:
        collector.collect(adapter=FailingAdapter(), provider="aliyun", source_id=source_id, now=now)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected provider failure")

    assert repository.get_checkpoint(source_id) is None
    database.close()

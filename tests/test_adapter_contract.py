from datetime import datetime, timezone, timedelta

import pytest

from src.ingestion.models import QueryRequest
from src.ingestion.adapters.base import BaseWAFAdapter


def test_query_request_requires_timezone_aware_datetimes():
    with pytest.raises(ValueError, match="timezone-aware"):
        QueryRequest(
            source_id="test",
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 1, 2),
        )


def test_query_request_rejects_invalid_time_range():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="earlier"):
        QueryRequest(source_id="test", start_time=now, end_time=now)


def test_cursor_round_trip():
    payload = {"offset": 200, "source": "sls"}
    encoded = BaseWAFAdapter.encode_cursor(payload)
    assert BaseWAFAdapter.decode_cursor(encoded) == payload


def test_filter_builder_rejects_unknown_fields():
    with pytest.raises(ValueError, match="Unsupported"):
        BaseWAFAdapter.build_filter_expression(
            {"untrusted_dsl": "* | select *"},
            {"action": "action"},
        )


def test_filter_builder_quotes_values():
    expression = BaseWAFAdapter.build_filter_expression(
        {"action": ['block" OR *']},
        {"action": "action"},
    )
    assert expression == '(action:"block\\" OR *")'

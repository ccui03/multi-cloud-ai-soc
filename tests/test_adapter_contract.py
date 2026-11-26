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



def test_aliyun_filter_fields_follow_official_waf_schema():
    from src.ingestion.adapters.aliyun_fields import ALIYUN_FILTER_FIELDS

    assert ALIYUN_FILTER_FIELDS == {
        "action": "final_action",
        "source_ip": "real_client_ip",
        "hostname": "host",
        "attack_type": "final_rule_type",
        "rule_id": "final_rule_id",
        "http_method": "request_method",
    }


def test_aliyun_final_action_mapping_does_not_assume_allow():
    from src.ingestion.adapters.aliyun_fields import normalize_final_action

    assert normalize_final_action("block") == "block"
    assert normalize_final_action("captcha") == "challenge"
    assert normalize_final_action(None) == "unknown"
    assert normalize_final_action("unexpected") == "unknown"

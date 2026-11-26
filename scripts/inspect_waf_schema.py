"""Inspect a small WAF log sample without printing log values or secrets.

The script reports field names, observed JSON types, occurrence counts, and
provider metadata. It intentionally does not print raw log values.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any

from src.ingestion.adapters import AliyunSLSAdapter, TencentCLSAdapter
from src.ingestion.config import load_aliyun_config, load_tencent_config
from src.ingestion.models import QueryRequest
from src.ingestion.adapters.aliyun_fields import ALIYUN_SAFE_ENUM_FIELDS


SENSITIVE_KEY_PARTS = (
    "cookie", "authorization", "token", "secret", "password", "passwd",
    "credential", "session", "phone", "mobile", "email", "user", "account",
    "identity", "id_card", "身份证", "手机号", "邮箱",
)
MAX_ENUM_VALUES = 10
MAX_ENUM_VALUE_LENGTH = 80


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def collect_schema(value: Any, prefix: str, schema: dict[str, dict[str, Any]]) -> None:
    """Collect dotted field paths and types, including nested JSON objects."""
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            entry = schema.setdefault(path, {"types": set(), "count": 0})
            entry["types"].add(value_type(child))
            entry["count"] += 1
            if isinstance(child, dict):
                collect_schema(child, path, schema)
            elif isinstance(child, list) and child:
                item_types = {value_type(item) for item in child}
                entry["item_types"] = entry.get("item_types", set()) | item_types
                for item in child:
                    if isinstance(item, dict):
                        collect_schema(item, path + "[]", schema)


def collect_safe_value_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Count values only for an explicit allowlist of low-risk enum-like fields."""
    stats: dict[str, dict[str, int]] = {}
    for record in records:
        for field in ALIYUN_SAFE_ENUM_FIELDS:
            if field not in record:
                continue
            value = record[field]
            if value is None:
                normalized = "(null)"
            elif isinstance(value, (dict, list)):
                normalized = f"({value_type(value)})"
            else:
                normalized = str(value).strip() or "(empty)"
            # Bound output length; never inspect arbitrary request/header fields.
            normalized = normalized[:MAX_ENUM_VALUE_LENGTH]
            field_stats = stats.setdefault(field, {})
            field_stats[normalized] = field_stats.get(normalized, 0) + 1
    return stats


def build_adapter(provider: str, env_dir: str):
    if provider == "aliyun":
        config = load_aliyun_config(f"{env_dir}/.env.aliyun")
        return AliyunSLSAdapter(**config)
    config = load_tencent_config(f"{env_dir}/.env.tencent")
    return TencentCLSAdapter(**config)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect WAF field names/types and selected safe enum values."
    )
    parser.add_argument("--provider", choices=("aliyun", "tencent"), required=True)
    parser.add_argument("--env-dir", default=".")
    parser.add_argument("--records", type=int, default=5)
    parser.add_argument("--lookback-minutes", type=int, default=15)
    args = parser.parse_args()

    if not 1 <= args.records <= 20:
        parser.error("--records must be between 1 and 20")
    if not 1 <= args.lookback_minutes <= 1440:
        parser.error("--lookback-minutes must be between 1 and 1440")

    env_dir = args.env_dir.rstrip("/\\")
    adapter = build_adapter(args.provider, env_dir)
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=args.lookback_minutes)
    source_id = (
        f"aliyun:{adapter.project}:{adapter.logstore}"
        if args.provider == "aliyun"
        else f"tencent:{adapter.topic_id}"
    )

    page = adapter.fetch_page(QueryRequest(
        source_id=source_id,
        start_time=start,
        end_time=end,
        page_size=args.records,
    ))

    schema: dict[str, dict[str, Any]] = {}
    raw_records = [record.raw for record in page.records]
    for raw in raw_records:
        collect_schema(raw, "", schema)

    print(f"provider: {args.provider}")
    print(f"source_id: {source_id}")
    print(f"time_range_utc: {start.isoformat()} .. {end.isoformat()}")
    print(f"records_returned: {len(page.records)}")
    print(f"has_more: {page.has_more}")
    print(f"provider_request_id: {page.provider_request_id or 'n/a'}")
    print("\nObserved fields (values are intentionally omitted):")
    if not schema:
        print("  No fields returned. Check the time range, source configuration, and query permissions.")
    else:
        for path in sorted(schema):
            entry = schema[path]
            types = ", ".join(sorted(entry["types"]))
            item_types = entry.get("item_types")
            suffix = f"; array_items={','.join(sorted(item_types))}" if item_types else ""
            sensitive = " [sensitive-name]" if is_sensitive_key(path.split(".")[-1].replace("[]", "")) else ""
            print(f"  {path}: types={types}; present_in_records={entry['count']}{suffix}{sensitive}")

    print("\nSafe enum value counts (allowlisted fields only):")
    enum_stats = collect_safe_value_stats(raw_records)
    if not enum_stats:
        print("  No allowlisted enum fields were present.")
    else:
        for field in ALIYUN_SAFE_ENUM_FIELDS:
            values = enum_stats.get(field)
            if not values:
                continue
            ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))
            print(f"  {field}:")
            for value, count in ordered[:MAX_ENUM_VALUES]:
                print(f"    {value!r}: {count}")
            if len(ordered) > MAX_ENUM_VALUES:
                print(f"    ... {len(ordered) - MAX_ENUM_VALUES} additional distinct values omitted")

    print("\nPrivacy: only allowlisted enum-like values are shown; request URLs, IPs, headers, cookies, and credentials are not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

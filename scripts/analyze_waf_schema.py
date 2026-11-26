"""Batch-profile WAF log schemas from supported cloud adapters."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.ingestion.adapters import AliyunSLSAdapter, TencentCLSAdapter
from src.ingestion.adapters.aliyun_fields import ALIYUN_SAFE_ENUM_FIELDS
from src.ingestion.config import load_aliyun_config, load_tencent_config
from src.ingestion.models import QueryRequest
from src.ingestion.schema_profiler import profile_records, render_profile

# Vendor-specific allowlists are deliberately separate from the generic profiler.
# Add a new vendor here only after reviewing its documented field semantics.
SAFE_ENUM_FIELDS = {
    "aliyun": ALIYUN_SAFE_ENUM_FIELDS,
    "tencent": (),
}


def build_adapter(provider: str, env_dir: str):
    if provider == "aliyun":
        return AliyunSLSAdapter(**load_aliyun_config(f"{env_dir}/.env.aliyun"))
    return TencentCLSAdapter(**load_tencent_config(f"{env_dir}/.env.tencent"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch profile WAF log schemas and same-record security-field relationships."
    )
    parser.add_argument("--provider", choices=("aliyun", "tencent"), required=True)
    parser.add_argument("--env-dir", default=".")
    parser.add_argument("--records", type=int, default=500, help="Maximum records to inspect (1-1000).")
    parser.add_argument("--page-size", type=int, default=200, help="Records per provider request (1-1000).")
    parser.add_argument("--lookback-hours", type=int, default=24, help="Time window (1-168 hours).")
    args = parser.parse_args()

    if not 1 <= args.records <= 1000:
        parser.error("--records must be between 1 and 1000")
    if not 1 <= args.page_size <= 1000:
        parser.error("--page-size must be between 1 and 1000")
    if not 1 <= args.lookback_hours <= 168:
        parser.error("--lookback-hours must be between 1 and 168")

    env_dir = args.env_dir.rstrip("/\\")
    adapter = build_adapter(args.provider, env_dir)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=args.lookback_hours)
    source_id = (
        f"aliyun:{adapter.project}:{adapter.logstore}"
        if args.provider == "aliyun"
        else f"tencent:{adapter.topic_id}"
    )

    records = []
    cursor = None
    request_ids = []
    pages = 0
    has_more = False
    while len(records) < args.records:
        request = QueryRequest(
            source_id=source_id,
            start_time=start,
            end_time=end,
            page_size=min(args.page_size, args.records - len(records)),
            cursor=cursor,
        )
        page = adapter.fetch_page(request)
        pages += 1
        if page.provider_request_id:
            request_ids.append(page.provider_request_id)
        records.extend(record.raw for record in page.records)
        has_more = page.has_more
        if not page.has_more or not page.next_cursor:
            break
        cursor = page.next_cursor

    safe_fields = SAFE_ENUM_FIELDS[args.provider]
    profile = profile_records(records, safe_enum_fields=safe_fields)

    print(f"provider: {args.provider}")
    print(f"source_id: {source_id}")
    print(f"time_range_utc: {start.isoformat()} .. {end.isoformat()}")
    print(f"records_returned: {len(records)}")
    print(f"pages_fetched: {pages}")
    print(f"reached_record_cap: {len(records) >= args.records and has_more}")
    print(f"has_more: {has_more}")
    print(f"provider_request_ids: {', '.join(request_ids[:5]) or 'n/a'}")
    print()
    print(render_profile(profile, safe_enum_fields=safe_fields))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

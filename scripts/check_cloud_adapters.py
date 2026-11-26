"""Manual connectivity smoke test. Does not print credentials or log contents."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.ingestion.adapters import AliyunSLSAdapter, TencentCLSAdapter
from src.ingestion.config import load_aliyun_config, load_tencent_config
from src.ingestion.models import QueryRequest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("aliyun", "tencent", "both"), default="both")
    parser.add_argument("--env-dir", default=".")
    args = parser.parse_args()
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=15)
    env_dir = args.env_dir.rstrip("/\\")
    checks = []
    if args.provider in ("aliyun", "both"):
        config = load_aliyun_config(f"{env_dir}/.env.aliyun")
        checks.append(("aliyun", AliyunSLSAdapter(**config)))
    if args.provider in ("tencent", "both"):
        config = load_tencent_config(f"{env_dir}/.env.tencent")
        checks.append(("tencent", TencentCLSAdapter(**config)))
    failed = False
    for provider, adapter in checks:
        try:
            page = adapter.fetch_page(QueryRequest(
                source_id=f"{provider}-waf-poc",
                start_time=start,
                end_time=end,
                page_size=5,
            ))
            print(f"{provider}: OK; records={len(page.records)}; has_more={page.has_more}; request_id={page.provider_request_id or 'n/a'}")
        except Exception as exc:
            failed = True
            print(f"{provider}: FAILED; {type(exc).__name__}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

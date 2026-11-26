"""Alibaba Cloud SLS read-only adapter (GetLogs API)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models import FetchPage, QueryRequest, RawWAFRecord, ensure_utc
from .base import BaseWAFAdapter, InvalidQuery, ProviderUnavailable


SLS_FILTER_FIELDS = {
    "action": "action",
    "source_ip": "remote_addr",
    "hostname": "host",
    "attack_type": "attack_type",
    "rule_id": "rule_id",
    "http_method": "http_method",
}


class AliyunSLSAdapter(BaseWAFAdapter):
    provider = "aliyun"

    def __init__(
        self,
        *,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        project: str,
        logstore: str,
        region: str = "",
        client: Any | None = None,
    ) -> None:
        required = {
            "access_key_id": access_key_id,
            "access_key_secret": access_key_secret,
            "endpoint": endpoint,
            "project": project,
            "logstore": logstore,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError("Missing SLS configuration: " + ", ".join(missing))
        self.project = project
        self.logstore = logstore
        self.region = region
        if client is None:
            try:
                from aliyun.log import LogClient
                from aliyun.log.auth import AUTH_VERSION_4
            except ImportError as exc:
                raise RuntimeError("Install aliyun-log-python-sdk to use AliyunSLSAdapter") from exc
            client = LogClient(
                endpoint,
                access_key_id,
                access_key_secret,
                auth_version=AUTH_VERSION_4,
                region=region,
            )
        self.client = client

    def health_check(self) -> bool:
        # A bounded, one-row query validates both credentials and Logstore access.
        from ..models import QueryRequest
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        try:
            self.fetch_page(QueryRequest(
                source_id=f"aliyun:{self.project}:{self.logstore}",
                start_time=now - timedelta(minutes=5),
                end_time=now,
                page_size=1,
            ))
            return True
        except Exception:
            return False

    def _build_query(self, filters: dict[str, Any]) -> str:
        try:
            expression = self.build_filter_expression(filters, SLS_FILTER_FIELDS)
        except ValueError as exc:
            raise InvalidQuery(str(exc)) from exc
        return expression or "*"

    @staticmethod
    def _record_to_dict(item: Any) -> dict[str, Any]:
        contents = getattr(item, "contents", None)
        if contents is None and isinstance(item, dict):
            return dict(item)
        raw = dict(contents or {})
        item_time = getattr(item, "time", None)
        if item_time is not None:
            raw.setdefault("__time__", str(item_time))
        return raw

    def fetch_page(self, request: QueryRequest) -> FetchPage:
        start = ensure_utc(request.start_time)
        end = ensure_utc(request.end_time)
        cursor = self.decode_cursor(request.cursor)
        query = self._build_query(request.filters)
        cursor_scope = {"query": query, "start": start.isoformat(), "end": end.isoformat()}
        if cursor and any(cursor.get(key) != value for key, value in cursor_scope.items()):
            raise ValueError("SLS cursor cannot be reused with a different query or time range")
        offset = int(cursor.get("offset", 0))
        if offset < 0:
            raise ValueError("Invalid SLS offset cursor")
        try:
            from aliyun.log import GetLogsRequest
            sdk_request = GetLogsRequest(
                self.project,
                self.logstore,
                int(start.timestamp()),
                int(end.timestamp()),
                topic="",
                query=query,
                line=min(request.page_size, 1000),
                offset=offset,
                reverse=False,
            )
            response = self.client.get_logs(sdk_request)
            items = response.get_logs()
            records = []
            for item in items:
                raw = self._record_to_dict(item)
                event_time = self.parse_time(raw.get("__time__") or raw.get("time"))
                records.append(RawWAFRecord(
                    provider=self.provider,
                    source_id=request.source_id,
                    event_time=event_time,
                    raw=raw,
                ))
            has_more = len(items) >= min(request.page_size, 1000)
            next_cursor = self.encode_cursor({**cursor_scope, "offset": offset + len(items)}) if has_more and items else None
            request_id = request.request_id or ""
            provider_request_id = None
            headers = getattr(response, "headers", None)
            if isinstance(headers, dict):
                provider_request_id = headers.get("x-log-requestid") or headers.get("x-log-request-id")
            return FetchPage(
                records=records,
                next_cursor=next_cursor,
                has_more=has_more,
                source_id=request.source_id,
                request_id=request_id,
                query_start=start,
                query_end=end,
                provider_request_id=provider_request_id,
            )
        except InvalidQuery:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "invalid" in message or "syntax" in message:
                raise InvalidQuery("SLS query rejected") from exc
            raise ProviderUnavailable("SLS GetLogs request failed") from exc

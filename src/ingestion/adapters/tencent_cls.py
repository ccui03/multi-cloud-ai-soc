"""Tencent Cloud CLS read-only adapter (SearchLog API)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..models import FetchPage, QueryRequest, RawWAFRecord, ensure_utc
from .base import BaseWAFAdapter, InvalidQuery, ProviderUnavailable


CLS_FILTER_FIELDS = {
    "action": "action",
    "source_ip": "remote_addr",
    "hostname": "host",
    "attack_type": "attack_type",
    "rule_id": "rule_id",
    "http_method": "http_method",
}


class TencentCLSAdapter(BaseWAFAdapter):
    provider = "tencent"

    def __init__(
        self,
        *,
        secret_id: str,
        secret_key: str,
        endpoint: str = "cls.tencentcloudapi.com",
        region: str,
        topic_id: str,
        client: Any | None = None,
    ) -> None:
        required = {
            "secret_id": secret_id,
            "secret_key": secret_key,
            "region": region,
            "topic_id": topic_id,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError("Missing CLS configuration: " + ", ".join(missing))
        self.region = region
        self.topic_id = topic_id
        endpoint = endpoint or "cls.tencentcloudapi.com"
        if client is None:
            try:
                from tencentcloud.common import credential
                from tencentcloud.common.profile.client_profile import ClientProfile
                from tencentcloud.common.profile.http_profile import HttpProfile
                from tencentcloud.cls.v20201016 import cls_client
            except ImportError as exc:
                raise RuntimeError("Install tencentcloud-sdk-python-cls to use TencentCLSAdapter") from exc
            http_profile = HttpProfile()
            http_profile.endpoint = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
            profile = ClientProfile()
            profile.httpProfile = http_profile
            client = cls_client.ClsClient(
                credential.Credential(secret_id, secret_key),
                region,
                profile,
            )
        self.client = client

    def health_check(self) -> bool:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        try:
            self.fetch_page(QueryRequest(
                source_id=f"tencent:{self.topic_id}",
                start_time=now - timedelta(minutes=5),
                end_time=now,
                page_size=1,
            ))
            return True
        except Exception:
            return False

    def _build_query(self, filters: dict[str, Any]) -> str:
        try:
            return self.build_filter_expression(filters, CLS_FILTER_FIELDS)
        except ValueError as exc:
            raise InvalidQuery(str(exc)) from exc

    @staticmethod
    def _model_to_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return dict(item)
        if hasattr(item, "to_json_string"):
            return json.loads(item.to_json_string())
        result = {}
        for name in ("Time", "Content", "PkgId", "PkgLogId", "TopicId", "Source", "Filename"):
            value = getattr(item, name, None)
            if value is not None:
                result[name] = value
        return result

    def fetch_page(self, request: QueryRequest) -> FetchPage:
        start = ensure_utc(request.start_time)
        end = ensure_utc(request.end_time)
        cursor = self.decode_cursor(request.cursor)
        query = self._build_query(request.filters)
        cursor_scope = {"query": query, "start": start.isoformat(), "end": end.isoformat()}
        if cursor and any(cursor.get(key) != value for key, value in cursor_scope.items()):
            raise ValueError("CLS cursor cannot be reused with a different query or time range")
        context = cursor.get("context", "")
        try:
            from tencentcloud.cls.v20201016 import models
            sdk_request = models.SearchLogRequest()
            sdk_request.TopicId = self.topic_id
            sdk_request.From = int(start.timestamp() * 1000)
            sdk_request.To = int(end.timestamp() * 1000)
            sdk_request.QueryString = query
            sdk_request.Limit = min(request.page_size, 1000)
            sdk_request.Sort = "asc"
            sdk_request.QuerySyntax = 1
            sdk_request.UseNewAnalysis = True
            if context:
                sdk_request.Context = context
            response = self.client.SearchLog(sdk_request)
            results = getattr(response, "Results", None) or []
            records = []
            for item in results:
                raw = self._model_to_dict(item)
                content = raw.get("Content")
                provider_meta = {k: v for k, v in raw.items() if k != "Content"}
                if isinstance(content, str):
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            raw = {**parsed, "_cls": provider_meta}
                    except json.JSONDecodeError:
                        pass
                event_time = self.parse_time(
                    provider_meta.get("Time")
                    or raw.get("@timestamp")
                    or raw.get("__time__")
                )
                pkg_id = provider_meta.get("PkgId")
                pkg_log_id = provider_meta.get("PkgLogId")
                source_record_id = f"{pkg_id}:{pkg_log_id}" if pkg_id is not None and pkg_log_id is not None else None
                records.append(RawWAFRecord(
                    provider=self.provider,
                    source_id=request.source_id,
                    event_time=event_time,
                    raw=raw,
                    source_record_id=source_record_id,
                ))
            next_context = getattr(response, "Context", None) or ""
            list_over = bool(getattr(response, "ListOver", True))
            has_more = not list_over and bool(next_context)
            next_cursor = self.encode_cursor({**cursor_scope, "context": next_context}) if has_more else None
            return FetchPage(
                records=records,
                next_cursor=next_cursor,
                has_more=has_more,
                source_id=request.source_id,
                request_id=request.request_id,
                query_start=start,
                query_end=end,
                provider_request_id=getattr(response, "RequestId", None),
            )
        except Exception as exc:
            message = str(exc).lower()
            if "invalidcontext" in message or "context" in message and "invalid" in message:
                from .base import CursorExpired
                raise CursorExpired("CLS search context expired; restart the bounded time window") from exc
            if "queryerror" in message or "syntax" in message:
                raise InvalidQuery("CLS query rejected") from exc
            raise ProviderUnavailable("CLS SearchLog request failed") from exc

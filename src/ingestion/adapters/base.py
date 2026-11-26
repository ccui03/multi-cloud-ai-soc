"""Base contract and shared helpers for read-only WAF log adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import base64
import json


class AdapterError(RuntimeError):
    """Base adapter exception."""


class AuthenticationError(AdapterError):
    pass


class PermissionDenied(AdapterError):
    pass


class RateLimited(AdapterError):
    pass


class QueryTimeout(AdapterError):
    pass


class InvalidQuery(AdapterError):
    pass


class CursorExpired(AdapterError):
    pass


class ProviderUnavailable(AdapterError):
    pass


class BaseWAFAdapter(ABC):
    provider: str

    @abstractmethod
    def health_check(self) -> bool:
        """Check credentials and access to the configured log source."""

    @abstractmethod
    def fetch_page(self, request: Any) -> Any:
        """Fetch one page using the shared QueryRequest / FetchPage contract."""

    @staticmethod
    def encode_cursor(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def decode_cursor(cursor: str | None) -> dict[str, Any]:
        if not cursor:
            return {}
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(padded.encode()))
            if not isinstance(value, dict):
                raise ValueError("cursor payload must be an object")
            return value
        except Exception as exc:
            raise ValueError("Invalid adapter cursor") from exc

    @staticmethod
    def parse_time(value: Any) -> datetime | None:
        if value is None or value == "":
            return None
        try:
            if isinstance(value, (int, float)):
                # Provider log timestamps may be seconds or milliseconds.
                stamp = float(value)
                if stamp > 10_000_000_000:
                    stamp /= 1000
                return datetime.fromtimestamp(stamp, tz=timezone.utc)
            if isinstance(value, str):
                text = value.strip()
                if text.isdigit():
                    return BaseWAFAdapter.parse_time(int(text))
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return None
        return None

    @staticmethod
    def build_filter_expression(filters: dict[str, Any], allowed_fields: dict[str, str]) -> str:
        """Build a conservative field query; never accept caller-supplied DSL."""
        clauses: list[str] = []
        for key, value in sorted(filters.items()):
            field_name = allowed_fields.get(key)
            if not field_name:
                raise ValueError(f"Unsupported filter field: {key}")
            values = value if isinstance(value, (list, tuple, set)) else [value]
            if not values:
                continue
            escaped = []
            for item in values:
                text = str(item).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
                escaped.append(f'{field_name}:"{text}"')
            clauses.append("(" + " OR ".join(escaped) + ")")
        return " AND ".join(clauses)

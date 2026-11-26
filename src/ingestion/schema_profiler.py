"""Vendor-neutral WAF log schema profiling helpers."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable

SENSITIVE_KEY_PARTS = (
    "cookie", "authorization", "token", "secret", "password", "passwd",
    "credential", "session", "phone", "mobile", "email", "user", "account",
    "identity", "id_card", "身份证", "手机号", "邮箱", "body", "payload",
    "querystring", "request_uri", "request_path", "referer", "forwarded_for",
    "remote_addr", "client_ip", "source_ip", "src_ip",
)
SECURITY_FIELD_SUFFIXES = (
    "_action", "_test", "_rule_id", "_rule_type", "_plugin", "_module",
    "_severity", "_category", "_attack_type", "_event_type",
)
SECURITY_FIELD_NAMES = {
    "action", "final_action", "final_plugin", "rule_id", "rule_type",
    "attack_type", "event_type", "severity", "risk_level", "bypass_matched_ids",
}
MAX_ENUM_VALUE_LENGTH = 64
MAX_ENUM_VALUES = 12


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


def is_security_field(path: str) -> bool:
    leaf = path.rsplit(".", 1)[-1].replace("[]", "").lower()
    return leaf in SECURITY_FIELD_NAMES or leaf.endswith(SECURITY_FIELD_SUFFIXES)


def collect_schema(value: Any, prefix: str, schema: dict[str, dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        entry = schema.setdefault(path, {"types": set(), "count": 0})
        entry["types"].add(value_type(child))
        entry["count"] += 1
        if isinstance(child, dict):
            collect_schema(child, path, schema)
        elif isinstance(child, list) and child:
            entry.setdefault("item_types", set()).update(value_type(item) for item in child)
            for item in child:
                if isinstance(item, dict):
                    collect_schema(item, path + "[]", schema)


def profile_records(
    records: Iterable[dict[str, Any]],
    safe_enum_fields: Iterable[str] = (),
) -> dict[str, Any]:
    """Profile field shape and co-occurrence without exposing arbitrary values.

    Values are counted only for explicitly allowlisted categorical fields.
    Security-field co-occurrence is calculated per record, not from aggregate
    field counts, so relationships such as final_action + scene_test are visible.
    """
    rows = list(records)
    schema: dict[str, dict[str, Any]] = {}
    safe_fields = set(safe_enum_fields)
    enum_counts: dict[str, Counter[str]] = {}
    security_presence: Counter[tuple[str, ...]] = Counter()
    security_field_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()

    for row in rows:
        collect_schema(row, "", schema)
        present = sorted(
            path for path in row
            if is_security_field(path)
        )
        security_presence[tuple(present)] += 1
        security_field_counts.update(present)
        pair_counts.update(combinations(present, 2))

        for field in safe_fields:
            if field not in row:
                continue
            value = row[field]
            if value is None:
                rendered = "(null)"
            elif isinstance(value, (dict, list)):
                rendered = f"({value_type(value)})"
            else:
                rendered = str(value).strip() or "(empty)"
            rendered = rendered[:MAX_ENUM_VALUE_LENGTH]
            enum_counts.setdefault(field, Counter())[rendered] += 1

    return {
        "record_count": len(rows),
        "schema": schema,
        "enum_counts": enum_counts,
        "security_field_counts": security_field_counts,
        "security_combinations": security_presence,
        "security_pair_counts": pair_counts,
    }


def render_profile(profile: dict[str, Any], safe_enum_fields: Iterable[str] = ()) -> str:
    lines: list[str] = []
    count = profile["record_count"]
    lines.append(f"Records profiled: {count}")
    lines.append("\nField schema (values omitted):")
    for path, entry in sorted(profile["schema"].items()):
        types = ",".join(sorted(entry["types"]))
        suffix = ""
        if entry.get("item_types"):
            suffix = "; array_items=" + ",".join(sorted(entry["item_types"]))
        sensitive = " [sensitive-name]" if is_sensitive_key(path.rsplit(".", 1)[-1]) else ""
        lines.append(f"  {path}: types={types}; present_in_records={entry['count']}{suffix}{sensitive}")

    lines.append("\nSecurity-field co-occurrence (same-record evidence):")
    fields = profile["security_field_counts"]
    if not fields:
        lines.append("  No recognized security fields found.")
    else:
        for field, field_count in sorted(fields.items()):
            lines.append(f"  {field}: {field_count}/{count}")
        lines.append("  Frequent field pairs:")
        pairs = profile["security_pair_counts"].most_common(30)
        if not pairs:
            lines.append("    No pairs observed.")
        for (left, right), pair_count in pairs:
            lines.append(f"    {left} + {right}: {pair_count}")
        lines.append("  Exact security-field combinations:")
        for combination, combo_count in profile["security_combinations"].most_common(20):
            if not combination:
                continue
            lines.append(f"    {', '.join(combination)}: {combo_count}")

    lines.append("\nSafe categorical value counts (explicit vendor allowlist only):")
    any_values = False
    for field in safe_enum_fields:
        values = profile["enum_counts"].get(field)
        if not values:
            continue
        any_values = True
        lines.append(f"  {field}:")
        for value, value_count in values.most_common(MAX_ENUM_VALUES):
            lines.append(f"    {value!r}: {value_count}")
        if len(values) > MAX_ENUM_VALUES:
            lines.append(f"    ... {len(values) - MAX_ENUM_VALUES} additional values omitted")
    if not any_values:
        lines.append("  No allowlisted categorical values were present.")

    lines.append("\nPrivacy: arbitrary log values are never printed; categorical values are shown only for explicitly allowlisted fields.")
    return "\n".join(lines)

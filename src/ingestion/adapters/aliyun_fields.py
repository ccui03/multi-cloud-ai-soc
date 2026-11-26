"""Official Alibaba Cloud WAF 3.0 log field metadata.

Source: https://help.aliyun.com/zh/waf/web-application-firewall-3-0/fields-in-logs
The registry describes documented semantics; field presence still depends on
WAF product support and optional log-delivery settings.
"""
from __future__ import annotations

# Canonical query fields exposed to the ingestion layer. These map the project's
# generic filter names to Alibaba WAF 3.0 documented SLS field names.
ALIYUN_FILTER_FIELDS = {
    "action": "final_action",
    "source_ip": "real_client_ip",
    "hostname": "host",
    "attack_type": "final_rule_type",
    "rule_id": "final_rule_id",
    "http_method": "request_method",
}

# Low-risk categorical fields only. Never add URLs, IPs, headers, cookies,
# request bodies, account identifiers, or arbitrary user-controlled values.
ALIYUN_SAFE_ENUM_FIELDS = (
    "status",
    "upstream_status",
    "request_method",
    "https",
    "server_protocol",
    "ssl_protocol",
    "final_action",
    "final_plugin",
    "final_rule_type",
    "waf_action",
    "waf_rule_type",
    "acl_action",
    "acl_rule_type",
    "acl_test",
    "cc_action",
    "cc_rule_type",
    "cc_test",
    "antiscan_action",
    "antiscan_rule_type",
    "antiscan_test",
    "scene_action",
    "scene_rule_type",
    "scene_test",
    "sema_action",
    "sema_rule_type",
    "sema_test",
    "major_protection_action",
    "major_protection_rule_type",
    "major_protection_test",
    "compliance_action",
    "compliance_rule_type",
    "compliance_test",
    "sema_action",
    "sema_rule_type",
    "sema_test",
    "compliance_action",
    "compliance_rule_type",
    "compliance_test",
    "dlp_action",
    "dlp_test",
    "bypass_matched_ids",
)

# Documented final_action values. The source value is always retained; this
# mapping is only a coarse common action category, not a replacement for it.
ALIYUN_FINAL_ACTION_MAP = {
    "block": "block",
    "monitor": "monitor",
    "bypass": "allow",
    "captcha_pass": "allow",
    "captcha_strict_pass": "allow",
    "js_pass": "allow",
    "sigchl_pass": "allow",
    "captcha_strict": "challenge",
    "captcha": "challenge",
    "sigchl": "challenge",
    "js": "challenge",
}


def normalize_final_action(value: object) -> str:
    """Map a documented final_action value; absence/unknown stays unknown.

    An absent final_action must not be interpreted as allow: Alibaba documents
    that it may be omitted when no protection module is triggered.
    """
    if value is None:
        return "unknown"
    return ALIYUN_FINAL_ACTION_MAP.get(str(value).strip().lower(), "unknown")



def classify_aliyun_action(raw: dict[str, object]) -> str:
    """Classify the best available documented WAF action evidence.

    Rule-module *_test=true means monitor mode even if *_action is block.
    An absent action is not evidence of allow; bypass_matched_ids is recorded
    separately as a matched allow-rule indicator.
    """
    final = raw.get("final_action")
    if final not in (None, ""):
        return normalize_final_action(final)

    # Module-level action fields can describe a rule hit even when final_action
    # is absent. Respect the corresponding test-mode flag before action value.
    modules = (
        "waf", "acl", "cc", "antiscan", "dlp", "scene",
        "major_protection", "compliance", "sema",
    )
    for module in modules:
        action = raw.get(f"{module}_action")
        if action in (None, ""):
            continue
        test = raw.get(f"{module}_test")
        if str(test).strip().lower() == "true":
            return "monitor"
        mapped = ALIYUN_FINAL_ACTION_MAP.get(str(action).strip().lower())
        if mapped:
            return mapped
        if str(action).strip().lower() in {
            "captcha_pass", "captcha_strict_pass", "js_pass", "sigchl_pass", "bypass"
        }:
            return "allow"
        if str(action).strip().lower() == "monitor":
            return "monitor"
        if str(action).strip().lower() == "filter":
            return "transform"
    return "unknown"

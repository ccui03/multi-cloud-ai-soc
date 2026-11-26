from src.ingestion.schema_profiler import profile_records, render_profile


def test_profile_reports_security_fields_that_cooccur_on_same_record():
    rows = [
        {"final_action": "block", "final_plugin": "scene", "scene_test": "true"},
        {"scene_action": "block", "scene_test": "false"},
        {"request_uri": "/sensitive?token=do-not-print"},
    ]
    profile = profile_records(rows, safe_enum_fields={"final_action", "scene_test"})
    assert profile["security_pair_counts"][("final_action", "final_plugin")] == 1
    assert profile["security_pair_counts"][("final_action", "scene_test")] == 1
    assert profile["security_pair_counts"][("scene_action", "scene_test")] == 1


def test_profile_does_not_print_non_allowlisted_values():
    rows = [{
        "http_cookie": "secret-cookie-value",
        "request_uri": "/path?password=secret",
        "final_action": "block",
    }]
    profile = profile_records(rows, safe_enum_fields={"final_action"})
    report = render_profile(profile, safe_enum_fields={"final_action"})
    assert "secret-cookie-value" not in report
    assert "/path?password=secret" not in report
    assert "'block'" in report


def test_profile_handles_nested_fields_and_arrays():
    profile = profile_records([{"nested": {"rule_type": "xss"}, "tags": ["a", "b"]}])
    assert "nested.rule_type" in profile["schema"]
    assert profile["schema"]["tags"]["item_types"] == {"string"}

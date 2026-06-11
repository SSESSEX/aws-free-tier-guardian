from datetime import datetime, timedelta, timezone

from app.scanner.iam_access_keys_rules import (
    calculate_age_days,
    evaluate_key_status,
    evaluate_key_age,
    evaluate_last_used,
    evaluate_access_key,
)


def test_calculate_age_days_from_datetime():
    date_value = datetime.now(timezone.utc) - timedelta(days=10)

    result = calculate_age_days(date_value)

    assert result == 10


def test_calculate_age_days_from_iso_string():
    date_value = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    result = calculate_age_days(date_value)

    assert result == 5


def test_active_key_status_returns_info():
    access_key = {
        "status": "Active"
    }

    result = evaluate_key_status(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_ACTIVE"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_inactive_key_status_returns_pass():
    access_key = {
        "status": "Inactive"
    }

    result = evaluate_key_status(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_INACTIVE"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_unknown_key_status_returns_warn():
    access_key = {
        "status": "Unknown"
    }

    result = evaluate_key_status(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_UNKNOWN_STATUS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_active_key_under_90_days_returns_pass():
    access_key = {
        "status": "Active",
        "age_days": 10,
    }

    result = evaluate_key_age(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_AGE"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_active_key_over_90_days_returns_warn():
    access_key = {
        "status": "Active",
        "age_days": 100,
    }

    result = evaluate_key_age(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_AGE"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_active_key_over_180_days_returns_fail():
    access_key = {
        "status": "Active",
        "age_days": 200,
    }

    result = evaluate_key_age(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_AGE"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_inactive_key_age_returns_info():
    access_key = {
        "status": "Inactive",
        "age_days": 200,
    }

    result = evaluate_key_age(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_AGE_INACTIVE"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_active_key_never_used_returns_warn():
    access_key = {
        "status": "Active",
        "last_used_date": None,
        "last_used_age_days": None,
    }

    result = evaluate_last_used(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_NEVER_USED"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_active_key_stale_usage_returns_warn():
    access_key = {
        "status": "Active",
        "last_used_date": "2026-01-01T00:00:00+00:00",
        "last_used_age_days": 120,
    }

    result = evaluate_last_used(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_STALE_USAGE"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_active_key_recently_used_returns_pass():
    access_key = {
        "status": "Active",
        "last_used_date": "2026-06-11T00:00:00+00:00",
        "last_used_age_days": 0,
    }

    result = evaluate_last_used(access_key)

    assert result["check"] == "IAM_ACCESS_KEY_RECENTLY_USED"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_evaluate_access_key_returns_three_findings():
    access_key = {
        "status": "Active",
        "age_days": 5,
        "last_used_date": "2026-06-11T00:00:00+00:00",
        "last_used_age_days": 0,
    }

    results = evaluate_access_key(access_key)

    assert len(results) == 3
    assert results[0]["status"] == "INFO"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "PASS"
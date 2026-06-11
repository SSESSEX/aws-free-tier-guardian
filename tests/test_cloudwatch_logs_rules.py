from app.scanner.cloudwatch_logs_rules import (
    evaluate_retention_policy,
    evaluate_stored_bytes,
    evaluate_kms_key,
    evaluate_tags,
    evaluate_log_group,
)


def test_log_group_without_retention_policy_returns_warn():
    log_group = {
        "retention_in_days": None
    }

    result = evaluate_retention_policy(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_RETENTION"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_log_group_with_long_retention_returns_warn():
    log_group = {
        "retention_in_days": 400
    }

    result = evaluate_retention_policy(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_RETENTION"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_log_group_with_reasonable_retention_returns_pass():
    log_group = {
        "retention_in_days": 30
    }

    result = evaluate_retention_policy(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_RETENTION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_log_group_with_large_storage_returns_warn():
    log_group = {
        "stored_bytes": 1_000_000_000
    }

    result = evaluate_stored_bytes(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_STORAGE"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_log_group_with_some_storage_returns_info():
    log_group = {
        "stored_bytes": 5000
    }

    result = evaluate_stored_bytes(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_STORAGE"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_log_group_with_zero_storage_returns_pass():
    log_group = {
        "stored_bytes": 0
    }

    result = evaluate_stored_bytes(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_STORAGE"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_log_group_with_kms_key_returns_pass():
    log_group = {
        "kms_key_id_present": True
    }

    result = evaluate_kms_key(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_KMS_KEY"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_log_group_without_kms_key_returns_info():
    log_group = {
        "kms_key_id_present": False
    }

    result = evaluate_kms_key(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_KMS_KEY"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_required_tags_present_returns_pass():
    log_group = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    log_group = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(log_group)

    assert result["check"] == "CLOUDWATCH_LOG_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_log_group_returns_four_findings():
    log_group = {
        "retention_in_days": 30,
        "stored_bytes": 0,
        "kms_key_id_present": False,
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        },
    }

    results = evaluate_log_group(log_group)

    assert len(results) == 4
    assert results[0]["status"] == "PASS"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "INFO"
    assert results[3]["status"] == "PASS"
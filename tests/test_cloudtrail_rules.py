from app.scanner.cloudtrail_rules import (
    evaluate_trail_exists,
    evaluate_logging_enabled,
    evaluate_multi_region_trail,
    evaluate_log_file_validation,
    evaluate_s3_bucket_configured,
    evaluate_kms_encryption,
    evaluate_latest_delivery_error,
    evaluate_tags,
    evaluate_trail,
)


def test_no_cloudtrail_trails_returns_warn_high():
    trails = []

    result = evaluate_trail_exists(trails)

    assert result["check"] == "CLOUDTRAIL_TRAIL_EXISTS"
    assert result["status"] == "WARN"
    assert result["severity"] == "HIGH"


def test_cloudtrail_trails_exist_returns_pass():
    trails = [
        {"trail_name": "guardian-trail"}
    ]

    result = evaluate_trail_exists(trails)

    assert result["check"] == "CLOUDTRAIL_TRAIL_EXISTS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_logging_enabled_returns_pass():
    trail = {
        "is_logging": True
    }

    result = evaluate_logging_enabled(trail)

    assert result["check"] == "CLOUDTRAIL_LOGGING_ENABLED"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_logging_disabled_returns_fail_high():
    trail = {
        "is_logging": False
    }

    result = evaluate_logging_enabled(trail)

    assert result["check"] == "CLOUDTRAIL_LOGGING_ENABLED"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_logging_unknown_returns_warn_medium():
    trail = {
        "is_logging": None
    }

    result = evaluate_logging_enabled(trail)

    assert result["check"] == "CLOUDTRAIL_LOGGING_ENABLED"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_multi_region_trail_returns_pass():
    trail = {
        "is_multi_region_trail": True
    }

    result = evaluate_multi_region_trail(trail)

    assert result["check"] == "CLOUDTRAIL_MULTI_REGION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_single_region_trail_returns_warn():
    trail = {
        "is_multi_region_trail": False
    }

    result = evaluate_multi_region_trail(trail)

    assert result["check"] == "CLOUDTRAIL_MULTI_REGION"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_log_file_validation_enabled_returns_pass():
    trail = {
        "log_file_validation_enabled": True
    }

    result = evaluate_log_file_validation(trail)

    assert result["check"] == "CLOUDTRAIL_LOG_FILE_VALIDATION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_log_file_validation_disabled_returns_warn():
    trail = {
        "log_file_validation_enabled": False
    }

    result = evaluate_log_file_validation(trail)

    assert result["check"] == "CLOUDTRAIL_LOG_FILE_VALIDATION"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_s3_bucket_configured_returns_pass():
    trail = {
        "s3_bucket_name": "guardian-cloudtrail-logs"
    }

    result = evaluate_s3_bucket_configured(trail)

    assert result["check"] == "CLOUDTRAIL_S3_BUCKET"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_s3_bucket_missing_returns_fail():
    trail = {
        "s3_bucket_name": None
    }

    result = evaluate_s3_bucket_configured(trail)

    assert result["check"] == "CLOUDTRAIL_S3_BUCKET"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_kms_key_present_returns_pass():
    trail = {
        "kms_key_id_present": True
    }

    result = evaluate_kms_encryption(trail)

    assert result["check"] == "CLOUDTRAIL_KMS_KEY"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_kms_key_missing_returns_info():
    trail = {
        "kms_key_id_present": False
    }

    result = evaluate_kms_encryption(trail)

    assert result["check"] == "CLOUDTRAIL_KMS_KEY"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_latest_delivery_error_returns_warn():
    trail = {
        "latest_delivery_error": "S3 bucket does not exist"
    }

    result = evaluate_latest_delivery_error(trail)

    assert result["check"] == "CLOUDTRAIL_DELIVERY_ERROR"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_no_latest_delivery_error_returns_pass():
    trail = {
        "latest_delivery_error": None
    }

    result = evaluate_latest_delivery_error(trail)

    assert result["check"] == "CLOUDTRAIL_DELIVERY_ERROR"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_required_tags_present_returns_pass():
    trail = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(trail)

    assert result["check"] == "CLOUDTRAIL_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    trail = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(trail)

    assert result["check"] == "CLOUDTRAIL_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_trail_returns_seven_findings():
    trail = {
        "is_logging": True,
        "is_multi_region_trail": True,
        "log_file_validation_enabled": True,
        "s3_bucket_name": "guardian-cloudtrail-logs",
        "kms_key_id_present": False,
        "latest_delivery_error": None,
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        },
    }

    results = evaluate_trail(trail)

    assert len(results) == 7
    assert results[0]["status"] == "PASS"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "PASS"
    assert results[3]["status"] == "PASS"
    assert results[4]["status"] == "INFO"
    assert results[5]["status"] == "PASS"
    assert results[6]["status"] == "PASS"
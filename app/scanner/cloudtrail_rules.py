def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


def evaluate_trail_exists(trails):
    if not trails:
        return finding(
            "CLOUDTRAIL_TRAIL_EXISTS",
            "WARN",
            "HIGH",
            "No CloudTrail trail was found. Consider configuring a trail for long-term audit logging.",
        )

    return finding(
        "CLOUDTRAIL_TRAIL_EXISTS",
        "PASS",
        "LOW",
        f"{len(trails)} CloudTrail trail(s) found.",
    )


def evaluate_logging_enabled(trail):
    if trail.get("is_logging") is True:
        return finding(
            "CLOUDTRAIL_LOGGING_ENABLED",
            "PASS",
            "LOW",
            "CloudTrail logging is enabled.",
        )

    if trail.get("is_logging") is False:
        return finding(
            "CLOUDTRAIL_LOGGING_ENABLED",
            "FAIL",
            "HIGH",
            "CloudTrail trail exists but logging is disabled.",
        )

    return finding(
        "CLOUDTRAIL_LOGGING_ENABLED",
        "WARN",
        "MEDIUM",
        "CloudTrail logging status could not be determined.",
    )


def evaluate_multi_region_trail(trail):
    if trail.get("is_multi_region_trail") is True:
        return finding(
            "CLOUDTRAIL_MULTI_REGION",
            "PASS",
            "LOW",
            "CloudTrail trail is multi-region.",
        )

    return finding(
        "CLOUDTRAIL_MULTI_REGION",
        "WARN",
        "MEDIUM",
        "CloudTrail trail is not multi-region. Confirm this is intentional.",
    )


def evaluate_log_file_validation(trail):
    if trail.get("log_file_validation_enabled") is True:
        return finding(
            "CLOUDTRAIL_LOG_FILE_VALIDATION",
            "PASS",
            "LOW",
            "CloudTrail log file validation is enabled.",
        )

    return finding(
        "CLOUDTRAIL_LOG_FILE_VALIDATION",
        "WARN",
        "MEDIUM",
        "CloudTrail log file validation is not enabled.",
    )


def evaluate_s3_bucket_configured(trail):
    if trail.get("s3_bucket_name"):
        return finding(
            "CLOUDTRAIL_S3_BUCKET",
            "PASS",
            "LOW",
            "CloudTrail is configured to deliver logs to an S3 bucket.",
        )

    return finding(
        "CLOUDTRAIL_S3_BUCKET",
        "FAIL",
        "HIGH",
        "CloudTrail trail has no S3 bucket configured.",
    )


def evaluate_kms_encryption(trail):
    if trail.get("kms_key_id_present") is True:
        return finding(
            "CLOUDTRAIL_KMS_KEY",
            "PASS",
            "LOW",
            "CloudTrail uses a customer-managed KMS key.",
        )

    return finding(
        "CLOUDTRAIL_KMS_KEY",
        "INFO",
        "LOW",
        "CloudTrail does not use a customer-managed KMS key.",
    )


def evaluate_latest_delivery_error(trail):
    latest_delivery_error = trail.get("latest_delivery_error")

    if latest_delivery_error:
        return finding(
            "CLOUDTRAIL_DELIVERY_ERROR",
            "WARN",
            "MEDIUM",
            f"CloudTrail has a latest delivery error: {latest_delivery_error}",
        )

    return finding(
        "CLOUDTRAIL_DELIVERY_ERROR",
        "PASS",
        "LOW",
        "No latest CloudTrail delivery error detected.",
    )


def evaluate_tags(trail):
    tags = trail.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "CLOUDTRAIL_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"CloudTrail trail is missing recommended tags: {missing_tags}.",
        )

    return finding(
        "CLOUDTRAIL_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "CloudTrail trail has the recommended Project and Environment tags.",
    )


def evaluate_trail(trail):
    return [
        evaluate_logging_enabled(trail),
        evaluate_multi_region_trail(trail),
        evaluate_log_file_validation(trail),
        evaluate_s3_bucket_configured(trail),
        evaluate_kms_encryption(trail),
        evaluate_latest_delivery_error(trail),
        evaluate_tags(trail),
    ]
def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


def evaluate_retention_policy(log_group):
    retention_in_days = log_group.get("retention_in_days")

    if retention_in_days is None:
        return finding(
            "CLOUDWATCH_LOG_RETENTION",
            "WARN",
            "MEDIUM",
            "Log group has no retention policy and may retain logs indefinitely.",
        )

    if retention_in_days > 365:
        return finding(
            "CLOUDWATCH_LOG_RETENTION",
            "WARN",
            "LOW",
            f"Log group retention is {retention_in_days} days. Confirm this is intentional.",
        )

    return finding(
        "CLOUDWATCH_LOG_RETENTION",
        "PASS",
        "LOW",
        f"Log group retention is set to {retention_in_days} days.",
    )


def evaluate_stored_bytes(log_group):
    stored_bytes = log_group.get("stored_bytes", 0)

    if stored_bytes >= 1_000_000_000:
        return finding(
            "CLOUDWATCH_LOG_STORAGE",
            "WARN",
            "MEDIUM",
            f"Log group stores {stored_bytes} bytes. Check whether old logs should be expired.",
        )

    if stored_bytes > 0:
        return finding(
            "CLOUDWATCH_LOG_STORAGE",
            "INFO",
            "LOW",
            f"Log group stores {stored_bytes} bytes.",
        )

    return finding(
        "CLOUDWATCH_LOG_STORAGE",
        "PASS",
        "LOW",
        "Log group currently stores 0 bytes.",
    )


def evaluate_kms_key(log_group):
    if log_group.get("kms_key_id_present") is True:
        return finding(
            "CLOUDWATCH_LOG_KMS_KEY",
            "PASS",
            "LOW",
            "Log group uses a customer-managed KMS key.",
        )

    return finding(
        "CLOUDWATCH_LOG_KMS_KEY",
        "INFO",
        "LOW",
        "Log group does not use a customer-managed KMS key.",
    )


def evaluate_tags(log_group):
    tags = log_group.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "CLOUDWATCH_LOG_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"Log group is missing recommended tags: {missing_tags}.",
        )

    return finding(
        "CLOUDWATCH_LOG_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "Log group has the recommended Project and Environment tags.",
    )


def evaluate_log_group(log_group):
    return [
        evaluate_retention_policy(log_group),
        evaluate_stored_bytes(log_group),
        evaluate_kms_key(log_group),
        evaluate_tags(log_group),
    ]
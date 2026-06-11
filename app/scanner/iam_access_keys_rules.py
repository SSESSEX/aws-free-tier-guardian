from datetime import datetime, timezone


def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


def calculate_age_days(date_value):
    if date_value is None:
        return None

    if isinstance(date_value, str):
        date_value = datetime.fromisoformat(date_value.replace("Z", "+00:00"))

    if date_value.tzinfo is None:
        date_value = date_value.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    return (now - date_value).days


def evaluate_key_status(access_key):
    status = access_key.get("status")

    if status == "Active":
        return finding(
            "IAM_ACCESS_KEY_ACTIVE",
            "INFO",
            "LOW",
            "Access key is active.",
        )

    if status == "Inactive":
        return finding(
            "IAM_ACCESS_KEY_INACTIVE",
            "PASS",
            "LOW",
            "Access key is inactive and cannot be used for API requests.",
        )

    return finding(
        "IAM_ACCESS_KEY_UNKNOWN_STATUS",
        "WARN",
        "LOW",
        f"Access key has unexpected status: {status}.",
    )


def evaluate_key_age(access_key):
    status = access_key.get("status")
    age_days = access_key.get("age_days")

    if age_days is None:
        return finding(
            "IAM_ACCESS_KEY_AGE_UNKNOWN",
            "WARN",
            "LOW",
            "Access key age could not be determined.",
        )

    if status != "Active":
        return finding(
            "IAM_ACCESS_KEY_AGE_INACTIVE",
            "INFO",
            "LOW",
            f"Access key is {age_days} days old but is inactive.",
        )

    if age_days >= 180:
        return finding(
            "IAM_ACCESS_KEY_AGE",
            "FAIL",
            "HIGH",
            f"Active access key is {age_days} days old. Rotate or remove stale credentials.",
        )

    if age_days >= 90:
        return finding(
            "IAM_ACCESS_KEY_AGE",
            "WARN",
            "MEDIUM",
            f"Active access key is {age_days} days old. Consider rotating it.",
        )

    return finding(
        "IAM_ACCESS_KEY_AGE",
        "PASS",
        "LOW",
        f"Active access key is {age_days} days old.",
    )


def evaluate_last_used(access_key):
    status = access_key.get("status")
    last_used_date = access_key.get("last_used_date")
    last_used_age_days = access_key.get("last_used_age_days")

    if status != "Active":
        return finding(
            "IAM_ACCESS_KEY_LAST_USED_INACTIVE",
            "INFO",
            "LOW",
            "Access key is inactive, so last-used risk is lower.",
        )

    if last_used_date is None:
        return finding(
            "IAM_ACCESS_KEY_NEVER_USED",
            "WARN",
            "MEDIUM",
            "Active access key has no recorded last-used date. Confirm whether it is needed.",
        )

    if last_used_age_days is None:
        return finding(
            "IAM_ACCESS_KEY_LAST_USED_UNKNOWN",
            "WARN",
            "LOW",
            "Access key last-used age could not be determined.",
        )

    if last_used_age_days >= 90:
        return finding(
            "IAM_ACCESS_KEY_STALE_USAGE",
            "WARN",
            "MEDIUM",
            f"Active access key has not been used for {last_used_age_days} days.",
        )

    return finding(
        "IAM_ACCESS_KEY_RECENTLY_USED",
        "PASS",
        "LOW",
        f"Active access key was last used {last_used_age_days} days ago.",
    )


def evaluate_access_key(access_key):
    return [
        evaluate_key_status(access_key),
        evaluate_key_age(access_key),
        evaluate_last_used(access_key),
    ]
def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


def evaluate_instance_status(db_instance):
    status = db_instance.get("db_instance_status")

    if status == "available":
        return finding(
            "RDS_INSTANCE_RUNNING",
            "WARN",
            "MEDIUM",
            "RDS DB instance is running. Confirm this is intentional to avoid unwanted cost.",
        )

    if status == "stopped":
        return finding(
            "RDS_INSTANCE_STOPPED",
            "INFO",
            "LOW",
            "RDS DB instance is stopped.",
        )

    if status is None:
        return finding(
            "RDS_INSTANCE_STATUS_UNKNOWN",
            "WARN",
            "LOW",
            "RDS DB instance status could not be determined.",
        )

    return finding(
        "RDS_INSTANCE_STATUS",
        "INFO",
        "LOW",
        f"RDS DB instance status is {status}.",
    )


def evaluate_public_accessibility(db_instance):
    if db_instance.get("publicly_accessible") is True:
        return finding(
            "RDS_PUBLIC_ACCESS",
            "FAIL",
            "HIGH",
            "RDS DB instance is publicly accessible.",
        )

    return finding(
        "RDS_PUBLIC_ACCESS",
        "PASS",
        "LOW",
        "RDS DB instance is not publicly accessible.",
    )


def evaluate_storage_encryption(db_instance):
    if db_instance.get("storage_encrypted") is True:
        return finding(
            "RDS_STORAGE_ENCRYPTION",
            "PASS",
            "LOW",
            "RDS DB instance storage encryption is enabled.",
        )

    return finding(
        "RDS_STORAGE_ENCRYPTION",
        "WARN",
        "MEDIUM",
        "RDS DB instance storage encryption is not enabled.",
    )


def evaluate_backup_retention(db_instance):
    backup_retention_period = db_instance.get("backup_retention_period")

    if backup_retention_period is None:
        return finding(
            "RDS_BACKUP_RETENTION",
            "WARN",
            "LOW",
            "RDS backup retention period could not be determined.",
        )

    if backup_retention_period == 0:
        return finding(
            "RDS_BACKUP_RETENTION",
            "WARN",
            "MEDIUM",
            "RDS automated backups are disabled.",
        )

    return finding(
        "RDS_BACKUP_RETENTION",
        "PASS",
        "LOW",
        f"RDS automated backup retention is set to {backup_retention_period} day(s).",
    )


def evaluate_deletion_protection(db_instance):
    if db_instance.get("deletion_protection") is True:
        return finding(
            "RDS_DELETION_PROTECTION",
            "PASS",
            "LOW",
            "RDS deletion protection is enabled.",
        )

    return finding(
        "RDS_DELETION_PROTECTION",
        "WARN",
        "LOW",
        "RDS deletion protection is not enabled.",
    )


def evaluate_multi_az(db_instance):
    if db_instance.get("multi_az") is True:
        return finding(
            "RDS_MULTI_AZ",
            "INFO",
            "LOW",
            "RDS Multi-AZ is enabled. Confirm this is intentional for cost-sensitive environments.",
        )

    return finding(
        "RDS_MULTI_AZ",
        "PASS",
        "LOW",
        "RDS Multi-AZ is not enabled.",
    )


def evaluate_allocated_storage(db_instance):
    allocated_storage = db_instance.get("allocated_storage_gb")

    if allocated_storage is None:
        return finding(
            "RDS_ALLOCATED_STORAGE",
            "WARN",
            "LOW",
            "RDS allocated storage could not be determined.",
        )

    if allocated_storage >= 100:
        return finding(
            "RDS_ALLOCATED_STORAGE",
            "WARN",
            "MEDIUM",
            f"RDS allocated storage is {allocated_storage} GB. Confirm this is intentional.",
        )

    return finding(
        "RDS_ALLOCATED_STORAGE",
        "PASS",
        "LOW",
        f"RDS allocated storage is {allocated_storage} GB.",
    )


def evaluate_tags(db_instance):
    tags = db_instance.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "RDS_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"RDS DB instance is missing recommended tags: {missing_tags}.",
        )

    return finding(
        "RDS_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "RDS DB instance has the recommended Project and Environment tags.",
    )


def evaluate_db_instance(db_instance):
    return [
        evaluate_instance_status(db_instance),
        evaluate_public_accessibility(db_instance),
        evaluate_storage_encryption(db_instance),
        evaluate_backup_retention(db_instance),
        evaluate_deletion_protection(db_instance),
        evaluate_multi_az(db_instance),
        evaluate_allocated_storage(db_instance),
        evaluate_tags(db_instance),
    ]
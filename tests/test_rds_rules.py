from app.scanner.rds_rules import (
    evaluate_instance_status,
    evaluate_public_accessibility,
    evaluate_storage_encryption,
    evaluate_backup_retention,
    evaluate_deletion_protection,
    evaluate_multi_az,
    evaluate_allocated_storage,
    evaluate_tags,
    evaluate_db_instance,
)


def test_rds_available_instance_returns_warn():
    db_instance = {
        "db_instance_status": "available"
    }

    result = evaluate_instance_status(db_instance)

    assert result["check"] == "RDS_INSTANCE_RUNNING"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_rds_stopped_instance_returns_info():
    db_instance = {
        "db_instance_status": "stopped"
    }

    result = evaluate_instance_status(db_instance)

    assert result["check"] == "RDS_INSTANCE_STOPPED"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_rds_unknown_status_returns_warn():
    db_instance = {
        "db_instance_status": None
    }

    result = evaluate_instance_status(db_instance)

    assert result["check"] == "RDS_INSTANCE_STATUS_UNKNOWN"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_rds_other_status_returns_info():
    db_instance = {
        "db_instance_status": "modifying"
    }

    result = evaluate_instance_status(db_instance)

    assert result["check"] == "RDS_INSTANCE_STATUS"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_rds_publicly_accessible_returns_fail():
    db_instance = {
        "publicly_accessible": True
    }

    result = evaluate_public_accessibility(db_instance)

    assert result["check"] == "RDS_PUBLIC_ACCESS"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_rds_not_publicly_accessible_returns_pass():
    db_instance = {
        "publicly_accessible": False
    }

    result = evaluate_public_accessibility(db_instance)

    assert result["check"] == "RDS_PUBLIC_ACCESS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_storage_encrypted_returns_pass():
    db_instance = {
        "storage_encrypted": True
    }

    result = evaluate_storage_encryption(db_instance)

    assert result["check"] == "RDS_STORAGE_ENCRYPTION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_storage_not_encrypted_returns_warn():
    db_instance = {
        "storage_encrypted": False
    }

    result = evaluate_storage_encryption(db_instance)

    assert result["check"] == "RDS_STORAGE_ENCRYPTION"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_rds_backup_retention_unknown_returns_warn():
    db_instance = {
        "backup_retention_period": None
    }

    result = evaluate_backup_retention(db_instance)

    assert result["check"] == "RDS_BACKUP_RETENTION"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_rds_backup_retention_zero_returns_warn():
    db_instance = {
        "backup_retention_period": 0
    }

    result = evaluate_backup_retention(db_instance)

    assert result["check"] == "RDS_BACKUP_RETENTION"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_rds_backup_retention_enabled_returns_pass():
    db_instance = {
        "backup_retention_period": 7
    }

    result = evaluate_backup_retention(db_instance)

    assert result["check"] == "RDS_BACKUP_RETENTION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_deletion_protection_enabled_returns_pass():
    db_instance = {
        "deletion_protection": True
    }

    result = evaluate_deletion_protection(db_instance)

    assert result["check"] == "RDS_DELETION_PROTECTION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_deletion_protection_disabled_returns_warn():
    db_instance = {
        "deletion_protection": False
    }

    result = evaluate_deletion_protection(db_instance)

    assert result["check"] == "RDS_DELETION_PROTECTION"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_rds_multi_az_enabled_returns_info():
    db_instance = {
        "multi_az": True
    }

    result = evaluate_multi_az(db_instance)

    assert result["check"] == "RDS_MULTI_AZ"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_rds_multi_az_disabled_returns_pass():
    db_instance = {
        "multi_az": False
    }

    result = evaluate_multi_az(db_instance)

    assert result["check"] == "RDS_MULTI_AZ"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_allocated_storage_unknown_returns_warn():
    db_instance = {
        "allocated_storage_gb": None
    }

    result = evaluate_allocated_storage(db_instance)

    assert result["check"] == "RDS_ALLOCATED_STORAGE"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_rds_large_allocated_storage_returns_warn():
    db_instance = {
        "allocated_storage_gb": 100
    }

    result = evaluate_allocated_storage(db_instance)

    assert result["check"] == "RDS_ALLOCATED_STORAGE"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_rds_normal_allocated_storage_returns_pass():
    db_instance = {
        "allocated_storage_gb": 20
    }

    result = evaluate_allocated_storage(db_instance)

    assert result["check"] == "RDS_ALLOCATED_STORAGE"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_required_tags_present_returns_pass():
    db_instance = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(db_instance)

    assert result["check"] == "RDS_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_rds_missing_required_tags_returns_warn():
    db_instance = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(db_instance)

    assert result["check"] == "RDS_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_db_instance_returns_eight_findings():
    db_instance = {
        "db_instance_status": "available",
        "publicly_accessible": False,
        "storage_encrypted": True,
        "backup_retention_period": 7,
        "deletion_protection": True,
        "multi_az": False,
        "allocated_storage_gb": 20,
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        },
    }

    results = evaluate_db_instance(db_instance)

    assert len(results) == 8
    assert results[0]["status"] == "WARN"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "PASS"
    assert results[3]["status"] == "PASS"
    assert results[4]["status"] == "PASS"
    assert results[5]["status"] == "PASS"
    assert results[6]["status"] == "PASS"
    assert results[7]["status"] == "PASS"
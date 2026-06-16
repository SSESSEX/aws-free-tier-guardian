from app.reports.scan_summary import (
    get_resource_identifier,
    get_service_status,
    extract_findings,
    build_global_summary,
)


def test_get_resource_identifier_returns_first_available_value():
    resource = {
        "name": "",
        "bucket_name": "guardian-dev-bucket",
    }

    result = get_resource_identifier(
        resource=resource,
        id_fields=["name", "bucket_name"],
    )

    assert result == "guardian-dev-bucket"


def test_get_resource_identifier_returns_unknown_when_missing():
    resource = {}

    result = get_resource_identifier(
        resource=resource,
        id_fields=["name", "id"],
    )

    assert result == "unknown"


def test_get_service_status_defaults_to_pass_when_no_findings():
    service_summary = {
        "total_findings": 0,
        "warnings": 0,
        "failed": 0,
    }

    result = get_service_status(service_summary)

    assert result == "PASS"


def test_get_service_status_returns_warn_when_warnings_exist():
    service_summary = {
        "warnings": 1,
        "failed": 0,
    }

    result = get_service_status(service_summary)

    assert result == "WARN"


def test_get_service_status_returns_fail_when_failures_exist():
    service_summary = {
        "warnings": 1,
        "failed": 1,
    }

    result = get_service_status(service_summary)

    assert result == "FAIL"


def test_extract_findings_includes_account_findings():
    services = {
        "cloudtrail": {
            "summary": {
                "account_findings": [
                    {
                        "check": "CLOUDTRAIL_TRAIL_EXISTS",
                        "status": "WARN",
                        "severity": "HIGH",
                        "message": "No CloudTrail trail was found.",
                    }
                ]
            },
            "trails": [],
        }
    }

    findings = extract_findings(services)

    assert len(findings) == 1
    assert findings[0]["service"] == "cloudtrail"
    assert findings[0]["resource_type"] == "account"
    assert findings[0]["resource_id"] == "account"


def test_build_global_summary_counts_resources_and_findings():
    services = {
        "s3": {
            "summary": {
                "overall_status": "WARN",
            },
            "buckets": [
                {
                    "bucket_name": "guardian-dev-bucket",
                    "findings": [
                        {
                            "check": "S3_VERSIONING",
                            "status": "WARN",
                            "severity": "MEDIUM",
                            "message": "Bucket versioning is disabled.",
                        }
                    ],
                }
            ],
        },
        "iam_access_keys": {
            "summary": {
                "overall_status": "PASS",
            },
            "access_keys": [
                {
                    "masked_access_key_id": "AKIA********YJOY",
                    "findings": [
                        {
                            "check": "IAM_ACCESS_KEY_AGE",
                            "status": "PASS",
                            "severity": "LOW",
                            "message": "Access key is young.",
                        }
                    ],
                }
            ],
        },
        "cloudtrail": {
            "summary": {
                "overall_status": "WARN",
                "account_findings": [
                    {
                        "check": "CLOUDTRAIL_TRAIL_EXISTS",
                        "status": "WARN",
                        "severity": "HIGH",
                        "message": "No CloudTrail trail was found.",
                    }
                ],
            },
            "trails": [],
        },
    }

    summary = build_global_summary(services)

    assert summary["overall_status"] == "WARN"
    assert summary["services_scanned"] == 3
    assert summary["resources_scanned"] == 2
    assert summary["total_findings"] == 3
    assert summary["warnings"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 0
    assert summary["resources_by_service"]["s3"] == 1
    assert summary["resources_by_service"]["iam_access_keys"] == 1
    assert summary["resources_by_service"]["cloudtrail"] == 0
    assert summary["top_risks"][0]["check"] == "CLOUDTRAIL_TRAIL_EXISTS"


def test_build_global_summary_fail_overrides_warn():
    services = {
        "rds": {
            "summary": {
                "overall_status": "FAIL",
            },
            "db_instances": [
                {
                    "db_instance_identifier": "prod-db",
                    "findings": [
                        {
                            "check": "RDS_PUBLIC_ACCESS",
                            "status": "FAIL",
                            "severity": "HIGH",
                            "message": "RDS DB instance is publicly accessible.",
                        }
                    ],
                }
            ],
        },
        "s3": {
            "summary": {
                "overall_status": "WARN",
            },
            "buckets": [
                {
                    "bucket_name": "guardian-dev-bucket",
                    "findings": [
                        {
                            "check": "S3_VERSIONING",
                            "status": "WARN",
                            "severity": "MEDIUM",
                            "message": "Bucket versioning is disabled.",
                        }
                    ],
                }
            ],
        },
    }

    summary = build_global_summary(services)

    assert summary["overall_status"] == "FAIL"
    assert summary["failed"] == 1
    assert summary["warnings"] == 1
    assert summary["top_risks"][0]["check"] == "RDS_PUBLIC_ACCESS"
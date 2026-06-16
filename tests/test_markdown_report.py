from app.reports.markdown_report import (
    safe,
    markdown_table,
    build_resources_by_service_table,
    build_services_by_status_table,
    build_top_risks_table,
    build_service_summary_table,
    build_markdown_report,
)


def test_safe_converts_none_to_empty_string():
    assert safe(None) == ""


def test_safe_converts_value_to_string():
    assert safe(123) == "123"


def test_markdown_table_builds_basic_table():
    result = markdown_table(
        headers=["Name", "Status"],
        rows=[
            ["S3", "WARN"],
            ["IAM", "PASS"],
        ],
    )

    assert "| Name | Status |" in result
    assert "| --- | --- |" in result
    assert "| S3 | WARN |" in result
    assert "| IAM | PASS |" in result


def test_build_resources_by_service_table_includes_resource_counts():
    summary = {
        "resources_by_service": {
            "s3": 1,
            "ec2": 0,
        }
    }

    result = build_resources_by_service_table(summary)

    assert "| Service | Resources scanned |" in result
    assert "| s3 | 1 |" in result
    assert "| ec2 | 0 |" in result


def test_build_services_by_status_table_includes_statuses():
    summary = {
        "services_by_status": {
            "s3": "WARN",
            "iam_access_keys": "PASS",
        }
    }

    result = build_services_by_status_table(summary)

    assert "| Service | Status |" in result
    assert "| s3 | WARN |" in result
    assert "| iam_access_keys | PASS |" in result


def test_build_top_risks_table_returns_message_when_no_risks():
    summary = {
        "top_risks": []
    }

    result = build_top_risks_table(summary)

    assert result == "No FAIL or WARN findings detected."


def test_build_top_risks_table_includes_risk_details():
    summary = {
        "top_risks": [
            {
                "severity": "HIGH",
                "status": "WARN",
                "service": "cloudtrail",
                "resource_type": "account",
                "resource_id": "account",
                "check": "CLOUDTRAIL_TRAIL_EXISTS",
                "message": "No CloudTrail trail was found.",
            }
        ]
    }

    result = build_top_risks_table(summary)

    assert "| Severity | Status | Service | Resource type | Resource ID | Check | Message |" in result
    assert "| HIGH | WARN | cloudtrail | account | account | CLOUDTRAIL_TRAIL_EXISTS | No CloudTrail trail was found. |" in result


def test_build_service_summary_table_includes_service_metrics():
    services = {
        "s3": {
            "summary": {
                "overall_status": "WARN",
                "total_findings": 6,
                "passed": 5,
                "warnings": 1,
                "failed": 0,
                "info": 0,
            }
        }
    }

    result = build_service_summary_table(services)

    assert "| Service | Status | Total findings | Passed | Warnings | Failures | Info |" in result
    assert "| s3 | WARN | 6 | 5 | 1 | 0 | 0 |" in result


def test_build_markdown_report_includes_main_sections():
    report = {
        "scan_time": "2026-06-15T17:11:13+00:00",
        "aws_profile": "guardian-dev",
        "aws_region": "eu-west-2",
        "summary": {
            "overall_status": "WARN",
            "services_scanned": 2,
            "resources_scanned": 2,
            "total_findings": 2,
            "passed": 1,
            "warnings": 1,
            "failed": 0,
            "info": 0,
            "critical": 0,
            "high": 1,
            "medium": 0,
            "low": 1,
            "resources_by_service": {
                "s3": 1,
                "cloudtrail": 0,
            },
            "services_by_status": {
                "s3": "WARN",
                "cloudtrail": "WARN",
            },
            "top_risks": [
                {
                    "severity": "HIGH",
                    "status": "WARN",
                    "service": "cloudtrail",
                    "resource_type": "account",
                    "resource_id": "account",
                    "check": "CLOUDTRAIL_TRAIL_EXISTS",
                    "message": "No CloudTrail trail was found.",
                }
            ],
        },
        "services": {
            "s3": {
                "summary": {
                    "overall_status": "WARN",
                    "total_findings": 1,
                    "passed": 0,
                    "warnings": 1,
                    "failed": 0,
                    "info": 0,
                }
            },
            "cloudtrail": {
                "summary": {
                    "overall_status": "WARN",
                    "total_findings": 1,
                    "passed": 0,
                    "warnings": 1,
                    "failed": 0,
                    "info": 0,
                }
            },
        },
    }

    result = build_markdown_report(report)

    assert "# AWS Free-Tier Guardian Report" in result
    assert "## Scan metadata" in result
    assert "## Executive summary" in result
    assert "## Resources by service" in result
    assert "## Service status" in result
    assert "## Top risks" in result
    assert "## Service summaries" in result
    assert "No CloudTrail trail was found." in result
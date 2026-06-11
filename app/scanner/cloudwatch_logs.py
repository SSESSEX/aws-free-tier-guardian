from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from app.scanner.cloudwatch_logs_rules import evaluate_log_group


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
elif not os.getenv("AWS_PROFILE"):
    print(f"Warning: .env file not found at {ENV_PATH}. Using fallback defaults.")


AWS_PROFILE = os.getenv("AWS_PROFILE", "guardian-dev")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports")


def create_aws_session():
    return boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_DEFAULT_REGION,
    )


def get_resource_arn(log_group):
    arn = log_group.get("logGroupArn") or log_group.get("arn")

    if not arn:
        return None

    return arn.removesuffix(":*")


def get_log_group_tags(logs_client, resource_arn):
    if not resource_arn:
        return {}

    try:
        response = logs_client.list_tags_for_resource(
            resourceArn=resource_arn
        )
        return response.get("tags", {})
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code in {
            "AccessDeniedException",
            "ResourceNotFoundException",
            "InvalidParameterException",
        }:
            return {}

        raise


def list_log_groups(session):
    logs_client = session.client("logs")
    paginator = logs_client.get_paginator("describe_log_groups")

    log_groups = []

    for page in paginator.paginate():
        for log_group in page.get("logGroups", []):
            resource_arn = get_resource_arn(log_group)

            log_group_report = {
                "name": log_group.get("logGroupName"),
                "arn": resource_arn,
                "creation_time": log_group.get("creationTime"),
                "retention_in_days": log_group.get("retentionInDays"),
                "metric_filter_count": log_group.get("metricFilterCount"),
                "stored_bytes": log_group.get("storedBytes", 0),
                "kms_key_id_present": log_group.get("kmsKeyId") is not None,
                "log_group_class": log_group.get("logGroupClass"),
                "tags": get_log_group_tags(logs_client, resource_arn),
            }

            log_group_report["findings"] = evaluate_log_group(log_group_report)

            log_groups.append(log_group_report)

    return log_groups


def build_summary(log_groups):
    total_findings = 0
    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    for log_group in log_groups:
        for item in log_group.get("findings", []):
            total_findings += 1

            status = item.get("status")
            severity = item.get("severity")

            if status == "PASS":
                passed += 1
            elif status == "WARN":
                warnings += 1
            elif status == "FAIL":
                failed += 1
            elif status == "INFO":
                info += 1

            if severity == "CRITICAL":
                critical += 1
            elif severity == "HIGH":
                high += 1
            elif severity == "MEDIUM":
                medium += 1
            elif severity == "LOW":
                low += 1

    no_retention_policy = [
        log_group for log_group in log_groups
        if log_group.get("retention_in_days") is None
    ]

    total_stored_bytes = sum(
        log_group.get("stored_bytes", 0)
        for log_group in log_groups
    )

    overall_status = "PASS"

    if failed > 0:
        overall_status = "FAIL"
    elif warnings > 0:
        overall_status = "WARN"

    return {
        "total_log_groups": len(log_groups),
        "no_retention_policy": len(no_retention_policy),
        "total_stored_bytes": total_stored_bytes,
        "total_findings": total_findings,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "info": info,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "overall_status": overall_status,
    }


def write_report(data):
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "cloudwatch_logs_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting CloudWatch Logs scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    log_groups = list_log_groups(session)
    summary = build_summary(log_groups)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "log_group_count": len(log_groups),
        "summary": summary,
        "log_groups": log_groups,
    }

    report_path = write_report(report)

    print(f"Found {len(log_groups)} CloudWatch log group(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
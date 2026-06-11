from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from app.scanner.cloudtrail_rules import (
    evaluate_trail,
    evaluate_trail_exists,
)


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


def isoformat_or_none(value):
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def get_trail_status(cloudtrail_client, trail_identifier):
    if not trail_identifier:
        return {}

    try:
        return cloudtrail_client.get_trail_status(
            Name=trail_identifier
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code in {
            "TrailNotFoundException",
            "AccessDeniedException",
            "InvalidTrailNameException",
        }:
            return {}

        raise


def get_event_selectors(cloudtrail_client, trail_identifier):
    if not trail_identifier:
        return {}

    try:
        return cloudtrail_client.get_event_selectors(
            TrailName=trail_identifier
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code in {
            "TrailNotFoundException",
            "AccessDeniedException",
            "InvalidTrailNameException",
        }:
            return {}

        raise


def get_cloudtrail_tags(cloudtrail_client, trail_arn):
    if not trail_arn:
        return {}

    try:
        response = cloudtrail_client.list_tags(
            ResourceIdList=[trail_arn]
        )

        resource_tags = response.get("ResourceTagList", [])

        if not resource_tags:
            return {}

        tags_list = resource_tags[0].get("TagsList", [])

        return {
            tag.get("Key"): tag.get("Value")
            for tag in tags_list
            if tag.get("Key")
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code in {
            "ResourceNotFoundException",
            "AccessDeniedException",
            "InvalidTrailNameException",
        }:
            return {}

        raise


def summarize_event_selectors(event_selectors_response):
    basic_selectors = event_selectors_response.get("EventSelectors", [])
    advanced_selectors = event_selectors_response.get("AdvancedEventSelectors", [])

    include_management_events = any(
        selector.get("IncludeManagementEvents") is True
        for selector in basic_selectors
    )

    return {
        "basic_event_selectors_count": len(basic_selectors),
        "advanced_event_selectors_count": len(advanced_selectors),
        "include_management_events": include_management_events,
    }


def normalize_trail(cloudtrail_client, trail):
    trail_name = trail.get("Name")
    trail_arn = trail.get("TrailARN")
    trail_identifier = trail_arn or trail_name

    status = get_trail_status(cloudtrail_client, trail_identifier)
    event_selectors = get_event_selectors(cloudtrail_client, trail_identifier)
    event_selector_summary = summarize_event_selectors(event_selectors)

    trail_report = {
        "trail_name": trail_name,
        "trail_arn": trail_arn,
        "home_region": trail.get("HomeRegion"),
        "s3_bucket_name": trail.get("S3BucketName"),
        "s3_key_prefix": trail.get("S3KeyPrefix"),
        "sns_topic_name": trail.get("SnsTopicName"),
        "cloudwatch_logs_log_group_arn_present": trail.get("CloudWatchLogsLogGroupArn") is not None,
        "kms_key_id_present": trail.get("KmsKeyId") is not None,
        "is_multi_region_trail": trail.get("IsMultiRegionTrail"),
        "is_organization_trail": trail.get("IsOrganizationTrail"),
        "log_file_validation_enabled": trail.get("LogFileValidationEnabled"),
        "is_logging": status.get("IsLogging"),
        "latest_delivery_error": status.get("LatestDeliveryError"),
        "latest_notification_error": status.get("LatestNotificationError"),
        "latest_delivery_time": isoformat_or_none(status.get("LatestDeliveryTime")),
        "start_logging_time": isoformat_or_none(status.get("StartLoggingTime")),
        "stop_logging_time": isoformat_or_none(status.get("StopLoggingTime")),
        "event_selector_summary": event_selector_summary,
        "tags": get_cloudtrail_tags(cloudtrail_client, trail_arn),
    }

    trail_report["findings"] = evaluate_trail(trail_report)

    return trail_report


def list_cloudtrail_trails(session):
    cloudtrail_client = session.client("cloudtrail")

    response = cloudtrail_client.describe_trails(
        includeShadowTrails=True
    )

    trails = []

    for trail in response.get("trailList", []):
        trails.append(
            normalize_trail(
                cloudtrail_client=cloudtrail_client,
                trail=trail,
            )
        )

    return trails


def build_summary(trails):
    account_findings = [
        evaluate_trail_exists(trails)
    ]

    total_findings = 0
    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    all_findings = list(account_findings)

    for trail in trails:
        all_findings.extend(trail.get("findings", []))

    for item in all_findings:
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

    logging_disabled = [
        trail for trail in trails
        if trail.get("is_logging") is False
    ]

    non_multi_region_trails = [
        trail for trail in trails
        if trail.get("is_multi_region_trail") is False
    ]

    trails_without_log_file_validation = [
        trail for trail in trails
        if trail.get("log_file_validation_enabled") is False
    ]

    overall_status = "PASS"

    if failed > 0:
        overall_status = "FAIL"
    elif warnings > 0:
        overall_status = "WARN"

    return {
        "total_trails": len(trails),
        "logging_disabled": len(logging_disabled),
        "non_multi_region_trails": len(non_multi_region_trails),
        "trails_without_log_file_validation": len(trails_without_log_file_validation),
        "account_findings": account_findings,
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

    report_path = report_dir / "cloudtrail_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting CloudTrail scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    trails = list_cloudtrail_trails(session)
    summary = build_summary(trails)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "trail_count": len(trails),
        "summary": summary,
        "trails": trails,
    }

    report_path = write_report(report)

    print(f"Found {len(trails)} CloudTrail trail(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
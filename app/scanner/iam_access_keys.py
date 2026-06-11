from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

from app.scanner.iam_access_keys_rules import (
    calculate_age_days,
    evaluate_access_key,
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


def mask_access_key_id(access_key_id):
    if not access_key_id:
        return None

    if len(access_key_id) <= 8:
        return "****"

    return f"{access_key_id[:4]}{'*' * (len(access_key_id) - 8)}{access_key_id[-4:]}"


def list_iam_users(iam_client):
    paginator = iam_client.get_paginator("list_users")

    users = []

    for page in paginator.paginate():
        users.extend(page.get("Users", []))

    return users


def list_user_access_keys(iam_client, user_name):
    paginator = iam_client.get_paginator("list_access_keys")

    access_keys = []

    for page in paginator.paginate(UserName=user_name):
        access_keys.extend(page.get("AccessKeyMetadata", []))

    return access_keys


def get_access_key_last_used(iam_client, access_key_id):
    response = iam_client.get_access_key_last_used(
        AccessKeyId=access_key_id
    )

    return response.get("AccessKeyLastUsed", {})


def normalize_access_key(iam_client, user_name, access_key):
    access_key_id = access_key.get("AccessKeyId")
    create_date = access_key.get("CreateDate")

    last_used = get_access_key_last_used(iam_client, access_key_id)
    last_used_date = last_used.get("LastUsedDate")

    create_date_iso = create_date.isoformat() if create_date else None
    last_used_date_iso = last_used_date.isoformat() if last_used_date else None

    access_key_report = {
        "user_name": user_name,
        "masked_access_key_id": mask_access_key_id(access_key_id),
        "status": access_key.get("Status"),
        "create_date": create_date_iso,
        "age_days": calculate_age_days(create_date),
        "last_used_date": last_used_date_iso,
        "last_used_age_days": calculate_age_days(last_used_date),
        "last_used_service": last_used.get("ServiceName"),
        "last_used_region": last_used.get("Region"),
    }

    access_key_report["findings"] = evaluate_access_key(access_key_report)

    return access_key_report


def list_iam_access_keys(session):
    iam_client = session.client("iam")

    access_key_reports = []

    users = list_iam_users(iam_client)

    for user in users:
        user_name = user.get("UserName")
        access_keys = list_user_access_keys(iam_client, user_name)

        for access_key in access_keys:
            access_key_reports.append(
                normalize_access_key(
                    iam_client=iam_client,
                    user_name=user_name,
                    access_key=access_key,
                )
            )

    return access_key_reports


def build_summary(access_keys):
    total_findings = 0
    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    active_keys = [
        key for key in access_keys
        if key.get("status") == "Active"
    ]

    inactive_keys = [
        key for key in access_keys
        if key.get("status") == "Inactive"
    ]

    never_used_keys = [
        key for key in access_keys
        if key.get("last_used_date") is None
    ]

    keys_older_than_90_days = [
        key for key in access_keys
        if key.get("age_days") is not None and key.get("age_days") >= 90
    ]

    for access_key in access_keys:
        for item in access_key.get("findings", []):
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

    overall_status = "PASS"

    if failed > 0:
        overall_status = "FAIL"
    elif warnings > 0:
        overall_status = "WARN"

    return {
        "total_access_keys": len(access_keys),
        "active_keys": len(active_keys),
        "inactive_keys": len(inactive_keys),
        "never_used_keys": len(never_used_keys),
        "keys_older_than_90_days": len(keys_older_than_90_days),
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

    report_path = report_dir / "iam_access_keys_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting IAM Access Key scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    access_keys = list_iam_access_keys(session)
    summary = build_summary(access_keys)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "access_key_count": len(access_keys),
        "summary": summary,
        "access_keys": access_keys,
    }

    report_path = write_report(report)

    print(f"Found {len(access_keys)} IAM access key(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
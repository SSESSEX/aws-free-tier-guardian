from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

from app.scanner.security_group_rules import evaluate_security_group


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


def convert_tags_to_dict(tags):
    if not tags:
        return {}

    return {
        tag.get("Key"): tag.get("Value")
        for tag in tags
    }


def normalize_ip_permissions(ip_permissions):
    rules = []

    for permission in ip_permissions:
        rule = {
            "protocol": permission.get("IpProtocol"),
            "from_port": permission.get("FromPort"),
            "to_port": permission.get("ToPort"),
            "ipv4_ranges": [
                item.get("CidrIp")
                for item in permission.get("IpRanges", [])
                if item.get("CidrIp")
            ],
            "ipv6_ranges": [
                item.get("CidrIpv6")
                for item in permission.get("Ipv6Ranges", [])
                if item.get("CidrIpv6")
            ],
            "prefix_list_ids": [
                item.get("PrefixListId")
                for item in permission.get("PrefixListIds", [])
                if item.get("PrefixListId")
            ],
            "user_id_group_pairs": [
                item.get("GroupId")
                for item in permission.get("UserIdGroupPairs", [])
                if item.get("GroupId")
            ],
        }

        rules.append(rule)

    return rules


def list_security_groups(session):
    ec2_client = session.client("ec2")
    paginator = ec2_client.get_paginator("describe_security_groups")

    security_groups = []

    for page in paginator.paginate():
        for group in page.get("SecurityGroups", []):
            group_report = {
                "group_id": group.get("GroupId"),
                "group_name": group.get("GroupName"),
                "description": group.get("Description"),
                "vpc_id": group.get("VpcId"),
                "owner_id": group.get("OwnerId"),
                "inbound_rules": normalize_ip_permissions(group.get("IpPermissions", [])),
                "outbound_rules": normalize_ip_permissions(group.get("IpPermissionsEgress", [])),
                "tags": convert_tags_to_dict(group.get("Tags", [])),
            }

            group_report["findings"] = evaluate_security_group(group_report)

            security_groups.append(group_report)

    return security_groups


def build_summary(security_groups):
    total_findings = 0
    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    for group in security_groups:
        for item in group.get("findings", []):
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
        "total_security_groups": len(security_groups),
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

    report_path = report_dir / "security_group_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting Security Group scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    security_groups = list_security_groups(session)
    summary = build_summary(security_groups)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "security_group_count": len(security_groups),
        "summary": summary,
        "security_groups": security_groups,
    }

    report_path = write_report(report)

    print(f"Found {len(security_groups)} security group(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
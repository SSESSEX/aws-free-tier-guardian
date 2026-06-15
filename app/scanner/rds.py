from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from app.scanner.rds_rules import evaluate_db_instance


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


def get_rds_tags(rds_client, resource_arn):
    if not resource_arn:
        return {}

    try:
        response = rds_client.list_tags_for_resource(
            ResourceName=resource_arn
        )

        return {
            tag.get("Key"): tag.get("Value")
            for tag in response.get("TagList", [])
            if tag.get("Key")
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code in {
            "DBInstanceNotFound",
            "AccessDenied",
            "AccessDeniedException",
            "InvalidParameterValue",
        }:
            return {}

        raise


def normalize_vpc_security_groups(db_instance):
    return [
        {
            "vpc_security_group_id": group.get("VpcSecurityGroupId"),
            "status": group.get("Status"),
        }
        for group in db_instance.get("VpcSecurityGroups", [])
    ]


def normalize_db_instance(rds_client, db_instance):
    db_instance_arn = db_instance.get("DBInstanceArn")

    db_instance_report = {
        "db_instance_identifier": db_instance.get("DBInstanceIdentifier"),
        "db_instance_arn": db_instance_arn,
        "db_instance_class": db_instance.get("DBInstanceClass"),
        "engine": db_instance.get("Engine"),
        "engine_version": db_instance.get("EngineVersion"),
        "db_instance_status": db_instance.get("DBInstanceStatus"),
        "allocated_storage_gb": db_instance.get("AllocatedStorage"),
        "storage_type": db_instance.get("StorageType"),
        "storage_encrypted": db_instance.get("StorageEncrypted"),
        "kms_key_id_present": db_instance.get("KmsKeyId") is not None,
        "publicly_accessible": db_instance.get("PubliclyAccessible"),
        "multi_az": db_instance.get("MultiAZ"),
        "backup_retention_period": db_instance.get("BackupRetentionPeriod"),
        "deletion_protection": db_instance.get("DeletionProtection"),
        "availability_zone": db_instance.get("AvailabilityZone"),
        "secondary_availability_zone": db_instance.get("SecondaryAvailabilityZone"),
        "db_subnet_group_name": (
            db_instance.get("DBSubnetGroup", {}).get("DBSubnetGroupName")
            if db_instance.get("DBSubnetGroup")
            else None
        ),
        "vpc_security_groups": normalize_vpc_security_groups(db_instance),
        "iam_database_authentication_enabled": db_instance.get("IAMDatabaseAuthenticationEnabled"),
        "performance_insights_enabled": db_instance.get("PerformanceInsightsEnabled"),
        "monitoring_interval": db_instance.get("MonitoringInterval"),
        "instance_create_time": isoformat_or_none(db_instance.get("InstanceCreateTime")),
        "tags": get_rds_tags(rds_client, db_instance_arn),
    }

    db_instance_report["findings"] = evaluate_db_instance(db_instance_report)

    return db_instance_report


def list_rds_db_instances(session):
    rds_client = session.client("rds")
    paginator = rds_client.get_paginator("describe_db_instances")

    db_instances = []

    for page in paginator.paginate():
        for db_instance in page.get("DBInstances", []):
            db_instances.append(
                normalize_db_instance(
                    rds_client=rds_client,
                    db_instance=db_instance,
                )
            )

    return db_instances


def build_summary(db_instances):
    total_findings = 0
    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    running_instances = [
        db_instance for db_instance in db_instances
        if db_instance.get("db_instance_status") == "available"
    ]

    public_instances = [
        db_instance for db_instance in db_instances
        if db_instance.get("publicly_accessible") is True
    ]

    unencrypted_instances = [
        db_instance for db_instance in db_instances
        if db_instance.get("storage_encrypted") is False
    ]

    deletion_protection_disabled = [
        db_instance for db_instance in db_instances
        if db_instance.get("deletion_protection") is False
    ]

    for db_instance in db_instances:
        for item in db_instance.get("findings", []):
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
        "total_db_instances": len(db_instances),
        "running_instances": len(running_instances),
        "public_instances": len(public_instances),
        "unencrypted_instances": len(unencrypted_instances),
        "deletion_protection_disabled": len(deletion_protection_disabled),
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

    report_path = report_dir / "rds_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting RDS scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    db_instances = list_rds_db_instances(session)
    summary = build_summary(db_instances)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "db_instance_count": len(db_instances),
        "summary": summary,
        "db_instances": db_instances,
    }

    report_path = write_report(report)

    print(f"Found {len(db_instances)} RDS DB instance(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
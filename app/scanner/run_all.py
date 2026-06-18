from pathlib import Path
import json
import os
from datetime import datetime, timezone
import argparse

import boto3
from dotenv import load_dotenv

from app.scanner.s3 import list_s3_buckets, build_summary as build_s3_summary
from app.scanner.ec2 import list_ec2_instances, build_summary as build_ec2_summary
from app.scanner.ebs import list_ebs_volumes, build_summary as build_ebs_summary
from app.scanner.eip import list_elastic_ips, build_summary as build_eip_summary
from app.reports.markdown_report import write_markdown_report
from app.storage.postgres_writer import save_report_to_postgres
from app.reports.scan_summary import build_global_summary
from app.scanner.security_group import (
    list_security_groups,
    build_summary as build_security_group_summary,
)

from app.scanner.cloudwatch_logs import (
    list_log_groups,
    build_summary as build_cloudwatch_logs_summary,
)

from app.scanner.iam_access_keys import (
    list_iam_access_keys,
    build_summary as build_iam_access_keys_summary,
)

from app.scanner.cloudtrail import (
    list_cloudtrail_trails,
    build_summary as build_cloudtrail_summary,
)

from app.scanner.rds import (
    list_rds_db_instances,
    build_summary as build_rds_summary,
)

from app.scanner.budgets import (
    list_budgets,
    build_summary as build_budgets_summary,
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
    """Create a boto3 session using the AWS profile and region from .env."""
    return boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_DEFAULT_REGION
    )


def write_report(data):
    """Write the combined AWS scan result to a local JSON file."""
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "aws_guardian_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run AWS Free-Tier Guardian scanners."
    )

    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist scan results to PostgreSQL.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("Starting AWS Free-Tier Guardian scan...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    print("Running S3 scanner...")
    buckets = list_s3_buckets(session)
    s3_summary = build_s3_summary(buckets)

    print("Running EC2 scanner...")
    instances = list_ec2_instances(session)
    ec2_summary = build_ec2_summary(instances)

    print("Running EBS scanner...")
    volumes = list_ebs_volumes(session)
    ebs_summary = build_ebs_summary(volumes)

    print("Running Elastic IP scanner...")
    addresses = list_elastic_ips(session)
    eip_summary = build_eip_summary(addresses)

    print("Running Security Group scanner...")
    security_groups = list_security_groups(session)
    security_group_summary = build_security_group_summary(security_groups)

    print("Running CloudWatch Logs scanner...")
    log_groups = list_log_groups(session)
    cloudwatch_logs_summary = build_cloudwatch_logs_summary(log_groups)

    print("Running IAM Access Key scanner...")
    access_keys = list_iam_access_keys(session)
    iam_access_keys_summary = build_iam_access_keys_summary(access_keys)

    print("Running CloudTrail scanner...")
    cloudtrail_trails = list_cloudtrail_trails(session)
    cloudtrail_summary = build_cloudtrail_summary(cloudtrail_trails)

    print("Running RDS scanner...")
    rds_db_instances = list_rds_db_instances(session)
    rds_summary = build_rds_summary(rds_db_instances)

    print("Running AWS Budgets scanner...")
    budgets = list_budgets(session)
    budgets_summary = build_budgets_summary(budgets)

    services = {
        "s3": {
            "bucket_count": len(buckets),
            "summary": s3_summary,
            "buckets": buckets,
        },
        "ec2": {
            "instance_count": len(instances),
            "summary": ec2_summary,
            "instances": instances,
        },
        "ebs": {
            "volume_count": len(volumes),
            "summary": ebs_summary,
            "volumes": volumes,
        },
        "eip": {
            "elastic_ip_count": len(addresses),
            "summary": eip_summary,
            "elastic_ips": addresses,
        },
        "security_groups": {
            "security_group_count": len(security_groups),
            "summary": security_group_summary,
            "security_groups": security_groups,
        },
        "cloudwatch_logs": {
            "log_group_count": len(log_groups),
            "summary": cloudwatch_logs_summary,
            "log_groups": log_groups,
        },
        "iam_access_keys": {
            "access_key_count": len(access_keys),
            "summary": iam_access_keys_summary,
            "access_keys": access_keys,
        },
        "cloudtrail": {
            "trail_count": len(cloudtrail_trails),
            "summary": cloudtrail_summary,
            "trails": cloudtrail_trails,
        },
        "rds": {
            "db_instance_count": len(rds_db_instances),
            "summary": rds_summary,
            "db_instances": rds_db_instances,
        },
        "budgets": {
            "budget_count": len(budgets),
            "summary": budgets_summary,
            "budgets": budgets,
        },
    }

    global_summary = build_global_summary(services)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "summary": global_summary,
        "services": services,
    }

    report_path = write_report(report)

    markdown_report_path = write_markdown_report(
        report=report,
        output_dir=PROJECT_ROOT / REPORT_OUTPUT_DIR,
    )

    scan_run_id = None

    if args.write_db:
        scan_run_id = save_report_to_postgres(report)


    print("Scan complete.")
    print(f"S3 buckets found: {len(buckets)}")
    print(f"EC2 instances found: {len(instances)}")
    print(f"EBS volumes found: {len(volumes)}")
    print(f"Elastic IPs found: {len(addresses)}")
    print(f"Security groups found: {len(security_groups)}")
    print(f"CloudWatch log groups found: {len(log_groups)}")
    print(f"IAM access keys found: {len(access_keys)}")
    print(f"CloudTrail trails found: {len(cloudtrail_trails)}")
    print(f"RDS DB instances found: {len(rds_db_instances)}")
    print(f"AWS Budgets found: {len(budgets)}")
    print(f"Combined report written to: {report_path}")
    print(f"Markdown report written to: {markdown_report_path}")
    
    if scan_run_id is not None:
        print(f"Scan saved to PostgreSQL with scan_run_id: {scan_run_id}")
    else:
        print("PostgreSQL save skipped. Use --write-db to persist results.")

    print(f"Overall status: {global_summary['overall_status']}")
    print(f"Services scanned: {global_summary['services_scanned']}")
    print(f"Resources scanned: {global_summary['resources_scanned']}")
    print(f"Total findings: {global_summary['total_findings']}")
    print(f"Warnings: {global_summary['warnings']}")
    print(f"Failures: {global_summary['failed']}")

    if global_summary["top_risks"]:
        print("Top risks:")
        for risk in global_summary["top_risks"][:5]:
            print(
                f"- [{risk['severity']}] {risk['service']} / "
                f"{risk['resource_type']} / {risk['check']}: {risk['message']}"
        )


if __name__ == "__main__":
    main()
from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

from app.scanner.s3 import list_s3_buckets, build_summary as build_s3_summary
from app.scanner.ec2 import list_ec2_instances, build_summary as build_ec2_summary
from app.scanner.ebs import list_ebs_volumes, build_summary as build_ebs_summary
from app.scanner.eip import list_elastic_ips, build_summary as build_eip_summary
from app.scanner.security_group import (
    list_security_groups,
    build_summary as build_security_group_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if not ENV_PATH.exists():
    print(f"Warning: .env file not found at {ENV_PATH}. Using fallback defaults.")

load_dotenv(dotenv_path=ENV_PATH)


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


def main():
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

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "services": {
            "s3": {
                "bucket_count": len(buckets),
                "summary": s3_summary,
                "buckets": buckets
            },
            "ec2": {
                "instance_count": len(instances),
                "summary": ec2_summary,
                "instances": instances
            },
            "ebs": {
                "volume_count": len(volumes),
                "summary": ebs_summary,
                "volumes": volumes
            },
            "eip": {
                "elastic_ip_count": len(addresses),
                "summary": eip_summary,
                "elastic_ips": addresses
            },
            "security_groups": {
                "security_group_count": len(security_groups),
                "summary": security_group_summary,
                "security_groups": security_groups,
}
        }
    }

    report_path = write_report(report)

    print("Scan complete.")
    print(f"S3 buckets found: {len(buckets)}")
    print(f"EC2 instances found: {len(instances)}")
    print(f"EBS volumes found: {len(volumes)}")
    print(f"Combined report written to: {report_path}")
    print(f"Elastic IPs found: {len(addresses)}")
    print(f"Security groups found: {len(security_groups)}")


if __name__ == "__main__":
    main()
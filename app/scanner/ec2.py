from pathlib import Path
import json
import os
from datetime import datetime, timezone
from app.scanner.ec2_rules import evaluate_instance

import boto3
from dotenv import load_dotenv


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


def convert_tags_to_dict(tags):
    """Convert AWS tag list into a simple dictionary."""
    if not tags:
        return {}

    return {
        tag.get("Key"): tag.get("Value")
        for tag in tags
    }


def list_ec2_instances(session):
    """List EC2 instances in the configured AWS region."""
    ec2_client = session.client("ec2")

    paginator = ec2_client.get_paginator("describe_instances")

    instances = []

    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_report = {
                "instance_id": instance.get("InstanceId"),
                "instance_type": instance.get("InstanceType"),
                "state": instance.get("State", {}).get("Name"),
                "image_id": instance.get("ImageId"),
                "launch_time": instance.get("LaunchTime").isoformat()
                if instance.get("LaunchTime")
                else None,
                "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                "vpc_id": instance.get("VpcId"),
                "subnet_id": instance.get("SubnetId"),
                "private_ip_address": instance.get("PrivateIpAddress"),
                "public_ip_address": instance.get("PublicIpAddress"),
                "has_public_ip": instance.get("PublicIpAddress") is not None,
                "security_groups": [
                    {
                        "group_id": group.get("GroupId"),
                        "group_name": group.get("GroupName")
                    }
                    for group in instance.get("SecurityGroups", [])
                ],
                "monitoring_state": instance.get("Monitoring", {}).get("State"),
                "tags": convert_tags_to_dict(instance.get("Tags", []))
            }

            instance_report["findings"] = evaluate_instance(instance_report)

            instances.append(instance_report)

    return instances


def build_summary(instances):
    """Build a lifecycle-aware EC2 scan summary."""

    active_states = {"pending", "running", "stopping", "stopped"}

    running_instances = [
        instance for instance in instances
        if instance.get("state") == "running"
    ]

    stopped_instances = [
        instance for instance in instances
        if instance.get("state") == "stopped"
    ]

    terminated_instances = [
        instance for instance in instances
        if instance.get("state") == "terminated"
    ]

    active_instances = [
        instance for instance in instances
        if instance.get("state") in active_states
    ]

    active_public_ip_instances = [
        instance for instance in active_instances
        if instance.get("has_public_ip") is True
    ]

    return {
        "total_instances_seen": len(instances),
        "active_instances": len(active_instances),
        "running": len(running_instances),
        "stopped": len(stopped_instances),
        "terminated": len(terminated_instances),
        "active_with_public_ip": len(active_public_ip_instances)
    }


def write_report(data):
    """Write the EC2 scan result to a local JSON file."""
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "ec2_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting EC2 scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    instances = list_ec2_instances(session)
    summary = build_summary(instances)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "instance_count": len(instances),
        "summary": summary,
        "instances": instances
    }

    report_path = write_report(report)

    print(f"Found {len(instances)} EC2 instance(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
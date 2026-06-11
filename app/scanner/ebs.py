from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

from app.scanner.ebs_rules import evaluate_volume


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
        region_name=AWS_DEFAULT_REGION,
    )


def convert_tags_to_dict(tags):
    """Convert AWS tag list into a simple dictionary."""
    if not tags:
        return {}

    return {
        tag.get("Key"): tag.get("Value")
        for tag in tags
    }


def normalize_attachments(attachments):
    """Normalize EBS volume attachment data."""
    normalized = []

    for attachment in attachments:
        normalized.append({
            "instance_id": attachment.get("InstanceId"),
            "device": attachment.get("Device"),
            "state": attachment.get("State"),
            "attach_time": attachment.get("AttachTime").isoformat()
            if attachment.get("AttachTime")
            else None,
            "delete_on_termination": attachment.get("DeleteOnTermination"),
        })

    return normalized


def list_ebs_volumes(session):
    """List EBS volumes in the configured AWS region."""
    ec2_client = session.client("ec2")

    paginator = ec2_client.get_paginator("describe_volumes")

    volumes = []

    for page in paginator.paginate():
        for volume in page.get("Volumes", []):
            volume_report = {
                "volume_id": volume.get("VolumeId"),
                "volume_type": volume.get("VolumeType"),
                "state": volume.get("State"),
                "size_gib": volume.get("Size"),
                "iops": volume.get("Iops"),
                "throughput": volume.get("Throughput"),
                "encrypted": volume.get("Encrypted"),
                "kms_key_id_present": volume.get("KmsKeyId") is not None,
                "availability_zone": volume.get("AvailabilityZone"),
                "create_time": volume.get("CreateTime").isoformat()
                if volume.get("CreateTime")
                else None,
                "attachments": normalize_attachments(volume.get("Attachments", [])),
                "tags": convert_tags_to_dict(volume.get("Tags", [])),
            }

            volume_report["findings"] = evaluate_volume(volume_report)

            volumes.append(volume_report)

    return volumes


def build_summary(volumes):
    """Build a top-level EBS scan summary."""
    available_volumes = [
        volume for volume in volumes
        if volume.get("state") == "available"
    ]

    in_use_volumes = [
        volume for volume in volumes
        if volume.get("state") == "in-use"
    ]

    encrypted_volumes = [
        volume for volume in volumes
        if volume.get("encrypted") is True
    ]

    unencrypted_volumes = [
        volume for volume in volumes
        if volume.get("encrypted") is False
    ]

    total_size_gib = sum(
        volume.get("size_gib", 0)
        for volume in volumes
    )

    return {
        "total_volumes": len(volumes),
        "available_unattached": len(available_volumes),
        "in_use": len(in_use_volumes),
        "encrypted": len(encrypted_volumes),
        "unencrypted": len(unencrypted_volumes),
        "total_size_gib": total_size_gib,
    }


def write_report(data):
    """Write the EBS scan result to a local JSON file."""
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "ebs_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting EBS scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    volumes = list_ebs_volumes(session)
    summary = build_summary(volumes)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "volume_count": len(volumes),
        "summary": summary,
        "volumes": volumes,
    }

    report_path = write_report(report)

    print(f"Found {len(volumes)} EBS volume(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
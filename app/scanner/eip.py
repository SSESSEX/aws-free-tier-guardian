from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

from app.scanner.eip_rules import evaluate_address


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if not ENV_PATH.exists():
    print(f"Warning: .env file not found at {ENV_PATH}. Using fallback defaults.")

load_dotenv(dotenv_path=ENV_PATH)


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


def list_elastic_ips(session):
    """List Elastic IP addresses in the configured AWS region."""
    ec2_client = session.client("ec2")

    response = ec2_client.describe_addresses()

    addresses = []

    for address in response.get("Addresses", []):
        address_report = {
            "allocation_id": address.get("AllocationId"),
            "association_id": address.get("AssociationId"),
            "public_ip": address.get("PublicIp"),
            "private_ip_address": address.get("PrivateIpAddress"),
            "domain": address.get("Domain"),
            "instance_id": address.get("InstanceId"),
            "network_interface_id": address.get("NetworkInterfaceId"),
            "network_interface_owner_id": address.get("NetworkInterfaceOwnerId"),
            "associated": address.get("AssociationId") is not None,
            "tags": convert_tags_to_dict(address.get("Tags", [])),
        }

        address_report["findings"] = evaluate_address(address_report)

        addresses.append(address_report)

    return addresses


def build_summary(addresses):
    associated = [
        address for address in addresses
        if address.get("associated") is True
    ]

    unassociated = [
        address for address in addresses
        if address.get("associated") is False
    ]

    return {
        "total_elastic_ips": len(addresses),
        "associated": len(associated),
        "unassociated": len(unassociated),
    }


def write_report(data):
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "eip_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting Elastic IP scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    addresses = list_elastic_ips(session)
    summary = build_summary(addresses)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "elastic_ip_count": len(addresses),
        "summary": summary,
        "elastic_ips": addresses,
    }

    report_path = write_report(report)

    print(f"Found {len(addresses)} Elastic IP address(es).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
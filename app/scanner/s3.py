from pathlib import Path
import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv


# Load .env from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)


AWS_PROFILE = os.getenv("AWS_PROFILE", "guardian-dev")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports")


def create_aws_session():
    """Create a boto3 session using the AWS profile from .env."""
    return boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_DEFAULT_REGION
    )


def list_s3_buckets(session):
    """List S3 buckets available to the configured AWS identity."""
    s3_client = session.client("s3")

    response = s3_client.list_buckets()

    buckets = []

    for bucket in response.get("Buckets", []):
        buckets.append({
            "name": bucket.get("Name"),
            "creation_date": bucket.get("CreationDate").isoformat()
            if bucket.get("CreationDate")
            else None
        })

    return buckets


def write_report(data):
    """Write the S3 scan result to a local JSON file."""
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "s3_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting S3 scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"AWS region: {AWS_DEFAULT_REGION}")

    session = create_aws_session()

    # Confirms which AWS identity boto3 is using
    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    buckets = list_s3_buckets(session)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "bucket_count": len(buckets),
        "buckets": buckets
    }

    report_path = write_report(report)

    print(f"Found {len(buckets)} S3 bucket(s).")
    print(f"Report written to: {report_path}")


if __name__ == "__main__":
    main()
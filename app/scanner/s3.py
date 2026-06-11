from pathlib import Path
import json
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from app.scanner.s3_rules import evaluate_bucket
from app.reports.markdown_report import write_markdown_report

import boto3
from dotenv import load_dotenv


# Load .env from the project root
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
    """Create a boto3 session using the AWS profile from .env."""
    return boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_DEFAULT_REGION
    )


def list_s3_buckets(session):
    """List S3 buckets and enrich each bucket with security/configuration settings."""
    s3_client = session.client("s3")

    response = s3_client.list_buckets()

    buckets = []

    for bucket in response.get("Buckets", []):
        bucket_name = bucket.get("Name")
        creation_date = bucket.get("CreationDate")

        bucket_report = {
            "name": bucket_name,
            "creation_date": creation_date.isoformat() if creation_date else None,
            "region": get_bucket_region(session, bucket_name),
            "public_access_block": get_bucket_public_access_block(session, bucket_name),
            "encryption": get_bucket_encryption(session, bucket_name),
            "versioning": get_bucket_versioning(session, bucket_name),
            "policy_status": get_bucket_policy_status(session, bucket_name),
            "ownership_controls": get_bucket_ownership_controls(session, bucket_name),
            "tags": get_bucket_tags(session, bucket_name),
            "policy": get_policy(session, bucket_name)
        }

        bucket_report["findings"] = evaluate_bucket(bucket_report)

        buckets.append(bucket_report)

    return buckets

def get_bucket_region(session, bucket_name):
    """Retrieve the AWS region where the S3 bucket lives."""
    s3 = session.client("s3")

    response = s3.get_bucket_location(Bucket=bucket_name)
    location = response.get("LocationConstraint")

    if location is None:
        return "us-east-1"

    if location == "EU":
        return "eu-west-1"

    return location


def get_bucket_public_access_block(session, bucket_name):
    """Retrieve bucket-level public access block settings."""
    s3 = session.client("s3")

    try:
        response = s3.get_public_access_block(Bucket=bucket_name)
        return response.get("PublicAccessBlockConfiguration")

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code == "NoSuchPublicAccessBlockConfiguration":
            return None

        raise


def get_bucket_encryption(session, bucket_name):
    """Retrieve default bucket encryption settings."""
    s3 = session.client("s3")

    try:
        response = s3.get_bucket_encryption(Bucket=bucket_name)
        rules = response.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])

        if not rules:
            return {
                "enabled": False,
                "algorithm": None
            }

        default_encryption = rules[0].get("ApplyServerSideEncryptionByDefault", {})

        return {
            "enabled": True,
            "algorithm": default_encryption.get("SSEAlgorithm"),
            "bucket_key_enabled": rules[0].get("BucketKeyEnabled")
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code == "ServerSideEncryptionConfigurationNotFoundError":
            return {
                "enabled": False,
                "algorithm": None
            }

        raise


def get_bucket_versioning(session, bucket_name):
    """Retrieve bucket versioning status."""
    s3 = session.client("s3")

    response = s3.get_bucket_versioning(Bucket=bucket_name)

    return {
        "status": response.get("Status", "Disabled"),
        "mfa_delete": response.get("MFADelete", "Disabled")
    }


def get_bucket_policy_status(session, bucket_name):
    """Check whether the bucket policy is public."""
    s3 = session.client("s3")

    try:
        response = s3.get_bucket_policy_status(Bucket=bucket_name)
        return {
            "is_public": response.get("PolicyStatus", {}).get("IsPublic")
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code in ["NoSuchBucketPolicy", "NoSuchBucket"]:
            return {
                "is_public": False
            }

        raise

def get_policy(session, bucket_name):
    """Retrieve bucket policy JSON string if one exists."""
    s3 = session.client("s3")

    try:
        result = s3.get_bucket_policy(Bucket=bucket_name)
        return result.get("Policy")

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code == "NoSuchBucketPolicy":
            return None

        raise


def get_bucket_ownership_controls(session, bucket_name):
    """Retrieve object ownership / ACL control settings."""
    s3 = session.client("s3")

    try:
        response = s3.get_bucket_ownership_controls(Bucket=bucket_name)
        rules = response.get("OwnershipControls", {}).get("Rules", [])

        if not rules:
            return {
                "object_ownership": None
            }

        return {
            "object_ownership": rules[0].get("ObjectOwnership")
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code == "OwnershipControlsNotFoundError":
            return {
                "object_ownership": None
            }

        raise


def get_bucket_tags(session, bucket_name):
    """Retrieve bucket tags as a simple dictionary."""
    s3 = session.client("s3")

    try:
        response = s3.get_bucket_tagging(Bucket=bucket_name)
        tag_set = response.get("TagSet", [])

        return {
            tag["Key"]: tag["Value"]
            for tag in tag_set
        }

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code == "NoSuchTagSet":
            return {}

        raise

def build_summary(buckets):
    """Build a top-level summary from all bucket findings."""
    summary = {
        "total_findings": 0,
        "passed": 0,
        "warnings": 0,
        "failed": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "overall_status": "PASS"
    }

    for bucket in buckets:
        for finding in bucket.get("findings", []):
            summary["total_findings"] += 1

            status = finding.get("status")
            severity = finding.get("severity")

            if status == "PASS":
                summary["passed"] += 1
            elif status == "WARN":
                summary["warnings"] += 1
            elif status == "FAIL":
                summary["failed"] += 1

            if severity == "CRITICAL":
                summary["critical"] += 1
            elif severity == "HIGH":
                summary["high"] += 1
            elif severity == "MEDIUM":
                summary["medium"] += 1
            elif severity == "LOW":
                summary["low"] += 1

    if summary["failed"] > 0:
        summary["overall_status"] = "FAIL"
    elif summary["warnings"] > 0:
        summary["overall_status"] = "WARN"

    return summary

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
    summary = build_summary(buckets)

    

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "bucket_count": len(buckets),
        "summary": summary,
        "buckets": buckets
    }

    report_path = write_report(report)

    markdown_report_path = PROJECT_ROOT / REPORT_OUTPUT_DIR / "s3_scan_report.md"
    write_markdown_report(report, markdown_report_path)

    print(f"Found {len(buckets)} S3 bucket(s).")
    print(f"JSON report written to: {report_path}")
    print(f"Markdown report written to: {markdown_report_path}")


if __name__ == "__main__":
    main()
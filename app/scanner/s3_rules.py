import os
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
import json

def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message
    }


def evaluate_public_access_block(bucket):
    config = bucket.get("public_access_block")

    required_settings = [
        "BlockPublicAcls",
        "IgnorePublicAcls",
        "BlockPublicPolicy",
        "RestrictPublicBuckets"
    ]

    if not config:
        return finding(
            "S3_PUBLIC_ACCESS_BLOCK",
            "FAIL",
            "HIGH",
            "Bucket does not have bucket-level public access block configuration."
        )

    missing_or_false = [
        setting for setting in required_settings
        if config.get(setting) is not True
    ]

    if missing_or_false:
        return finding(
            "S3_PUBLIC_ACCESS_BLOCK",
            "FAIL",
            "HIGH",
            f"Some public access block settings are not enabled: {missing_or_false}."
        )

    return finding(
        "S3_PUBLIC_ACCESS_BLOCK",
        "PASS",
        "LOW",
        "All bucket-level public access block settings are enabled."
    )


def evaluate_encryption(bucket):
    encryption = bucket.get("encryption", {})

    if encryption.get("enabled") is True:
        return finding(
            "S3_DEFAULT_ENCRYPTION",
            "PASS",
            "LOW",
            f"Bucket has default encryption enabled using {encryption.get('algorithm')}."
        )

    return finding(
        "S3_DEFAULT_ENCRYPTION",
        "FAIL",
        "HIGH",
        "Bucket does not have default encryption enabled."
    )


def evaluate_versioning(bucket):
    versioning = bucket.get("versioning", {})

    if versioning.get("status") == "Enabled":
        return finding(
            "S3_VERSIONING",
            "PASS",
            "LOW",
            "Bucket versioning is enabled."
        )

    return finding(
        "S3_VERSIONING",
        "WARN",
        "MEDIUM",
        "Bucket versioning is disabled. This may be acceptable for a dev bucket, but production buckets should usually enable versioning."
    )


def evaluate_policy_status(bucket):
    policy_status = bucket.get("policy_status", {})

    if policy_status.get("is_public") is True:
        return finding(
            "S3_BUCKET_POLICY_PUBLIC",
            "FAIL",
            "CRITICAL",
            "Bucket policy is public."
        )

    return finding(
        "S3_BUCKET_POLICY_PUBLIC",
        "PASS",
        "LOW",
        "Bucket policy is not public."
    )


def evaluate_ownership_controls(bucket):
    ownership = bucket.get("ownership_controls", {})

    if ownership.get("object_ownership") == "BucketOwnerEnforced":
        return finding(
            "S3_OBJECT_OWNERSHIP",
            "PASS",
            "LOW",
            "Bucket uses BucketOwnerEnforced ownership, meaning ACLs are disabled."
        )

    return finding(
        "S3_OBJECT_OWNERSHIP",
        "WARN",
        "MEDIUM",
        "Bucket does not use BucketOwnerEnforced ownership."
    )


def evaluate_tags(bucket):
    tags = bucket.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "S3_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"Bucket is missing recommended tags: {missing_tags}."
        )

    return finding(
        "S3_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "Bucket has the recommended Project and Environment tags."
    )


def evaluate_bucket(bucket):
    return [
        evaluate_public_access_block(bucket),
        evaluate_encryption(bucket),
        evaluate_versioning(bucket),
        evaluate_policy_status(bucket),
        evaluate_ownership_controls(bucket),
        evaluate_tags(bucket)
    ]

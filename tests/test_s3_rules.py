import os
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
import json

from app.scanner.s3_rules import (
    evaluate_public_access_block,
    evaluate_encryption,
    evaluate_versioning,
    evaluate_policy_status,
    evaluate_tags,
    evaluate_ownership_controls,
    evaluate_bucket,
)


def test_public_access_block_fully_enabled_returns_pass():
    bucket = {
        "public_access_block": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
    }

    result = evaluate_public_access_block(bucket)

    assert result["check"] == "S3_PUBLIC_ACCESS_BLOCK"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_public_access_block_missing_returns_fail():
    bucket = {
        "public_access_block": None
    }

    result = evaluate_public_access_block(bucket)

    assert result["check"] == "S3_PUBLIC_ACCESS_BLOCK"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_encryption_enabled_returns_pass():
    bucket = {
        "encryption": {
            "enabled": True,
            "algorithm": "AES256",
        }
    }

    result = evaluate_encryption(bucket)

    assert result["check"] == "S3_DEFAULT_ENCRYPTION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_encryption_disabled_returns_fail():
    bucket = {
        "encryption": {
            "enabled": False,
            "algorithm": None,
        }
    }

    result = evaluate_encryption(bucket)

    assert result["check"] == "S3_DEFAULT_ENCRYPTION"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_versioning_disabled_returns_warn():
    bucket = {
        "versioning": {
            "status": "Disabled",
            "mfa_delete": "Disabled",
        }
    }

    result = evaluate_versioning(bucket)

    assert result["check"] == "S3_VERSIONING"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_versioning_enabled_returns_pass():
    bucket = {
        "versioning": {
            "status": "Enabled",
            "mfa_delete": "Disabled",
        }
    }

    result = evaluate_versioning(bucket)

    assert result["check"] == "S3_VERSIONING"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_public_policy_returns_fail_critical():
    bucket = {
        "policy_status": {
            "is_public": True
        }
    }

    result = evaluate_policy_status(bucket)

    assert result["check"] == "S3_BUCKET_POLICY_PUBLIC"
    assert result["status"] == "FAIL"
    assert result["severity"] == "CRITICAL"


def test_private_policy_returns_pass():
    bucket = {
        "policy_status": {
            "is_public": False
        }
    }

    result = evaluate_policy_status(bucket)

    assert result["check"] == "S3_BUCKET_POLICY_PUBLIC"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_bucket_owner_enforced_returns_pass():
    bucket = {
        "ownership_controls": {
            "object_ownership": "BucketOwnerEnforced"
        }
    }

    result = evaluate_ownership_controls(bucket)

    assert result["check"] == "S3_OBJECT_OWNERSHIP"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_non_bucket_owner_enforced_returns_warn():
    bucket = {
        "ownership_controls": {
            "object_ownership": "ObjectWriter"
        }
    }

    result = evaluate_ownership_controls(bucket)

    assert result["check"] == "S3_OBJECT_OWNERSHIP"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_required_tags_present_returns_pass():
    bucket = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(bucket)

    assert result["check"] == "S3_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    bucket = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(bucket)

    assert result["check"] == "S3_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_bucket_returns_six_findings():
    bucket = {
        "public_access_block": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
        "encryption": {
            "enabled": True,
            "algorithm": "AES256",
        },
        "versioning": {
            "status": "Disabled",
            "mfa_delete": "Disabled",
        },
        "policy_status": {
            "is_public": False,
        },
        "ownership_controls": {
            "object_ownership": "BucketOwnerEnforced",
        },
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        },
    }

    results = evaluate_bucket(bucket)

    assert len(results) == 6
    assert results[0]["status"] == "PASS"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "WARN"
    assert results[3]["status"] == "PASS"
    assert results[4]["status"] == "PASS"
    assert results[5]["status"] == "PASS"
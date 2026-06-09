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
        "message": message,
    }


def evaluate_volume_state(volume):
    state = volume.get("state")

    if state == "available":
        return finding(
            "EBS_VOLUME_UNATTACHED",
            "WARN",
            "MEDIUM",
            "Volume is available/unattached. Check whether it is still needed because unattached EBS volumes can still incur storage cost.",
        )

    if state == "in-use":
        return finding(
            "EBS_VOLUME_ATTACHED",
            "PASS",
            "LOW",
            "Volume is attached to an EC2 instance.",
        )

    return finding(
        "EBS_VOLUME_STATE",
        "INFO",
        "LOW",
        f"Volume state is {state}.",
    )


def evaluate_encryption(volume):
    if volume.get("encrypted") is True:
        return finding(
            "EBS_ENCRYPTION",
            "PASS",
            "LOW",
            "Volume is encrypted.",
        )

    return finding(
        "EBS_ENCRYPTION",
        "FAIL",
        "HIGH",
        "Volume is not encrypted.",
    )


def evaluate_delete_on_termination(volume):
    attachments = volume.get("attachments", [])

    if not attachments:
        return finding(
            "EBS_DELETE_ON_TERMINATION",
            "WARN",
            "MEDIUM",
            "Volume is not attached, so delete-on-termination does not currently apply.",
        )

    delete_flags = [
        attachment.get("delete_on_termination")
        for attachment in attachments
    ]

    if all(delete_flags):
        return finding(
            "EBS_DELETE_ON_TERMINATION",
            "PASS",
            "LOW",
            "Attached volume is configured to delete on instance termination.",
        )

    return finding(
        "EBS_DELETE_ON_TERMINATION",
        "WARN",
        "MEDIUM",
        "Attached volume is not configured to delete on termination for all attachments.",
    )


def evaluate_tags(volume):
    tags = volume.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "EBS_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"Volume is missing recommended tags: {missing_tags}.",
        )

    return finding(
        "EBS_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "Volume has the recommended Project and Environment tags.",
    )


def evaluate_volume_size(volume):
    size_gib = volume.get("size_gib", 0)

    if size_gib > 30:
        return finding(
            "EBS_VOLUME_SIZE",
            "WARN",
            "LOW",
            f"Volume is {size_gib} GiB. Confirm this size is intentional for a dev environment.",
        )

    return finding(
        "EBS_VOLUME_SIZE",
        "PASS",
        "LOW",
        f"Volume size is {size_gib} GiB.",
    )


def evaluate_volume(volume):
    return [
        evaluate_volume_state(volume),
        evaluate_encryption(volume),
        evaluate_delete_on_termination(volume),
        evaluate_tags(volume),
        evaluate_volume_size(volume),
    ]
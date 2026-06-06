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


def evaluate_public_ip(instance):
    state = instance.get("state")

    if state == "terminated":
        return finding(
            "EC2_PUBLIC_IP_ATTACHED",
            "PASS",
            "LOW",
            "Instance is terminated, so public IPv4 exposure is no longer active."
        )

    if instance.get("has_public_ip") is True:
        return finding(
            "EC2_PUBLIC_IP_ATTACHED",
            "WARN",
            "MEDIUM",
            "Active instance has a public IPv4 address attached."
        )

    return finding(
        "EC2_PUBLIC_IP_ATTACHED",
        "PASS",
        "LOW",
        "Instance does not have a public IPv4 address."
    )


def evaluate_instance_state(instance):
    state = instance.get("state")

    if state == "running":
        return finding(
            "EC2_INSTANCE_RUNNING",
            "WARN",
            "MEDIUM",
            "Instance is currently running. Confirm it is still needed to avoid unnecessary cost."
        )

    if state == "stopped":
        return finding(
            "EC2_INSTANCE_STOPPED",
            "WARN",
            "LOW",
            "Instance is stopped. Check attached EBS volumes because storage may still cost money."
        )

    if state == "terminated":
        return finding(
            "EC2_INSTANCE_TERMINATED",
            "PASS",
            "LOW",
            "Instance is terminated."
        )

    return finding(
        "EC2_INSTANCE_STATE",
        "INFO",
        "LOW",
        f"Instance state is {state}."
    )


def evaluate_tags(instance):
    tags = instance.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "EC2_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"Instance is missing recommended tags: {missing_tags}."
        )

    return finding(
        "EC2_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "Instance has the recommended Project and Environment tags."
    )


def evaluate_monitoring(instance):
    monitoring_state = instance.get("monitoring_state")

    if monitoring_state == "enabled":
        return finding(
            "EC2_DETAILED_MONITORING",
            "INFO",
            "LOW",
            "Detailed monitoring is enabled."
        )

    return finding(
        "EC2_DETAILED_MONITORING",
        "PASS",
        "LOW",
        "Detailed monitoring is not enabled, which is acceptable for a small dev/test instance."
    )


def evaluate_instance(instance):
    return [
        evaluate_public_ip(instance),
        evaluate_instance_state(instance),
        evaluate_tags(instance),
        evaluate_monitoring(instance)
    ]
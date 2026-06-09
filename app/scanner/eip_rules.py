def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


def evaluate_association(address):
    if address.get("associated") is True:
        return finding(
            "EIP_ASSOCIATED",
            "PASS",
            "LOW",
            "Elastic IP is associated with a resource.",
        )

    return finding(
        "EIP_UNASSOCIATED",
        "WARN",
        "MEDIUM",
        "Elastic IP is allocated but not associated with any resource. Check whether it is still needed.",
    )


def evaluate_public_ip(address):
    if address.get("public_ip"):
        return finding(
            "EIP_PUBLIC_IPV4",
            "INFO",
            "LOW",
            "Elastic IP has a public IPv4 address.",
        )

    return finding(
        "EIP_PUBLIC_IPV4",
        "WARN",
        "LOW",
        "Elastic IP record has no public IPv4 value.",
    )


def evaluate_tags(address):
    tags = address.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "EIP_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"Elastic IP is missing recommended tags: {missing_tags}.",
        )

    return finding(
        "EIP_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "Elastic IP has the recommended Project and Environment tags.",
    )


def evaluate_address(address):
    return [
        evaluate_association(address),
        evaluate_public_ip(address),
        evaluate_tags(address),
    ]
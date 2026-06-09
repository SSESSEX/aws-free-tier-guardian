def finding(check, status, severity, message):
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "message": message,
    }


WORLD_IPV4 = "0.0.0.0/0"
WORLD_IPV6 = "::/0"

ADMIN_PORTS = {
    22: "SSH",
    3389: "RDP",
}

DATABASE_PORTS = {
    3306: "MySQL",
    5432: "PostgreSQL",
    1433: "SQL Server",
    1521: "Oracle",
    6379: "Redis",
    27017: "MongoDB",
}


def rule_allows_world(rule):
    ipv4_ranges = rule.get("ipv4_ranges", [])
    ipv6_ranges = rule.get("ipv6_ranges", [])

    return WORLD_IPV4 in ipv4_ranges or WORLD_IPV6 in ipv6_ranges


def port_in_range(port, from_port, to_port):
    if from_port is None or to_port is None:
        return False

    return from_port <= port <= to_port


def evaluate_world_open_admin_ports(security_group):
    risky_rules = []

    for rule in security_group.get("inbound_rules", []):
        if not rule_allows_world(rule):
            continue

        from_port = rule.get("from_port")
        to_port = rule.get("to_port")

        for port, service_name in ADMIN_PORTS.items():
            if port_in_range(port, from_port, to_port):
                risky_rules.append(f"{service_name} ({port})")

    if risky_rules:
        return finding(
            "SG_WORLD_OPEN_ADMIN_PORTS",
            "FAIL",
            "CRITICAL",
            f"Security group allows admin access from the internet: {sorted(set(risky_rules))}.",
        )

    return finding(
        "SG_WORLD_OPEN_ADMIN_PORTS",
        "PASS",
        "LOW",
        "Security group does not allow SSH/RDP from the internet.",
    )


def evaluate_world_open_database_ports(security_group):
    risky_rules = []

    for rule in security_group.get("inbound_rules", []):
        if not rule_allows_world(rule):
            continue

        from_port = rule.get("from_port")
        to_port = rule.get("to_port")

        for port, service_name in DATABASE_PORTS.items():
            if port_in_range(port, from_port, to_port):
                risky_rules.append(f"{service_name} ({port})")

    if risky_rules:
        return finding(
            "SG_WORLD_OPEN_DATABASE_PORTS",
            "FAIL",
            "HIGH",
            f"Security group allows database access from the internet: {sorted(set(risky_rules))}.",
        )

    return finding(
        "SG_WORLD_OPEN_DATABASE_PORTS",
        "PASS",
        "LOW",
        "Security group does not expose common database ports to the internet.",
    )


def evaluate_any_world_open_inbound(security_group):
    world_open_rules = [
        rule for rule in security_group.get("inbound_rules", [])
        if rule_allows_world(rule)
    ]

    if world_open_rules:
        return finding(
            "SG_WORLD_OPEN_INBOUND",
            "WARN",
            "MEDIUM",
            f"Security group has {len(world_open_rules)} inbound rule(s) open to the internet.",
        )

    return finding(
        "SG_WORLD_OPEN_INBOUND",
        "PASS",
        "LOW",
        "Security group has no inbound rules open to the internet.",
    )


def evaluate_missing_inbound_rules(security_group):
    inbound_rules = security_group.get("inbound_rules", [])

    if not inbound_rules:
        return finding(
            "SG_NO_INBOUND_RULES",
            "PASS",
            "LOW",
            "Security group has no inbound rules.",
        )

    return finding(
        "SG_HAS_INBOUND_RULES",
        "INFO",
        "LOW",
        f"Security group has {len(inbound_rules)} inbound rule(s).",
    )


def evaluate_tags(security_group):
    tags = security_group.get("tags", {})

    required_tags = ["Project", "Environment"]

    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:
        return finding(
            "SG_REQUIRED_TAGS",
            "WARN",
            "LOW",
            f"Security group is missing recommended tags: {missing_tags}.",
        )

    return finding(
        "SG_REQUIRED_TAGS",
        "PASS",
        "LOW",
        "Security group has the recommended Project and Environment tags.",
    )


def evaluate_security_group(security_group):
    return [
        evaluate_world_open_admin_ports(security_group),
        evaluate_world_open_database_ports(security_group),
        evaluate_any_world_open_inbound(security_group),
        evaluate_missing_inbound_rules(security_group),
        evaluate_tags(security_group),
    ]
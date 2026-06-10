from app.scanner.security_group_rules import (
    rule_allows_world,
    port_in_range,
    evaluate_world_open_admin_ports,
    evaluate_world_open_database_ports,
    evaluate_any_world_open_inbound,
    evaluate_missing_inbound_rules,
    evaluate_tags,
    evaluate_security_group,
)


def test_rule_allows_world_ipv4():
    rule = {
        "ipv4_ranges": ["0.0.0.0/0"],
        "ipv6_ranges": [],
    }

    assert rule_allows_world(rule) is True


def test_rule_allows_world_ipv6():
    rule = {
        "ipv4_ranges": [],
        "ipv6_ranges": ["::/0"],
    }

    assert rule_allows_world(rule) is True


def test_rule_does_not_allow_world():
    rule = {
        "ipv4_ranges": ["203.0.113.10/32"],
        "ipv6_ranges": [],
    }

    assert rule_allows_world(rule) is False


def test_port_in_range():
    assert port_in_range(22, 20, 30) is True
    assert port_in_range(22, 80, 443) is False
    assert port_in_range(22, None, None) is False


def test_world_open_ssh_returns_fail_critical():
    security_group = {
        "inbound_rules": [
            {
                "from_port": 22,
                "to_port": 22,
                "ipv4_ranges": ["0.0.0.0/0"],
                "ipv6_ranges": [],
            }
        ]
    }

    result = evaluate_world_open_admin_ports(security_group)

    assert result["check"] == "SG_WORLD_OPEN_ADMIN_PORTS"
    assert result["status"] == "FAIL"
    assert result["severity"] == "CRITICAL"


def test_no_world_open_admin_ports_returns_pass():
    security_group = {
        "inbound_rules": [
            {
                "from_port": 22,
                "to_port": 22,
                "ipv4_ranges": ["203.0.113.10/32"],
                "ipv6_ranges": [],
            }
        ]
    }

    result = evaluate_world_open_admin_ports(security_group)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_world_open_database_port_returns_fail_high():
    security_group = {
        "inbound_rules": [
            {
                "from_port": 5432,
                "to_port": 5432,
                "ipv4_ranges": ["0.0.0.0/0"],
                "ipv6_ranges": [],
            }
        ]
    }

    result = evaluate_world_open_database_ports(security_group)

    assert result["check"] == "SG_WORLD_OPEN_DATABASE_PORTS"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_no_world_open_database_ports_returns_pass():
    security_group = {
        "inbound_rules": [
            {
                "from_port": 5432,
                "to_port": 5432,
                "ipv4_ranges": ["203.0.113.10/32"],
                "ipv6_ranges": [],
            }
        ]
    }

    result = evaluate_world_open_database_ports(security_group)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_any_world_open_inbound_returns_warn():
    security_group = {
        "inbound_rules": [
            {
                "from_port": 80,
                "to_port": 80,
                "ipv4_ranges": ["0.0.0.0/0"],
                "ipv6_ranges": [],
            }
        ]
    }

    result = evaluate_any_world_open_inbound(security_group)

    assert result["check"] == "SG_WORLD_OPEN_INBOUND"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_no_inbound_rules_returns_pass():
    security_group = {
        "inbound_rules": []
    }

    result = evaluate_missing_inbound_rules(security_group)

    assert result["check"] == "SG_NO_INBOUND_RULES"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_required_tags_present_returns_pass():
    security_group = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(security_group)

    assert result["check"] == "SG_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    security_group = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(security_group)

    assert result["check"] == "SG_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_security_group_returns_five_findings():
    security_group = {
        "inbound_rules": [],
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    results = evaluate_security_group(security_group)

    assert len(results) == 5
    assert results[0]["status"] == "PASS"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "PASS"
    assert results[3]["status"] == "PASS"
    assert results[4]["status"] == "PASS"
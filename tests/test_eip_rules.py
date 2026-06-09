from app.scanner.eip_rules import (
    evaluate_association,
    evaluate_public_ip,
    evaluate_tags,
    evaluate_address,
)


def test_associated_elastic_ip_returns_pass():
    address = {
        "associated": True
    }

    result = evaluate_association(address)

    assert result["check"] == "EIP_ASSOCIATED"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_unassociated_elastic_ip_returns_warn():
    address = {
        "associated": False
    }

    result = evaluate_association(address)

    assert result["check"] == "EIP_UNASSOCIATED"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_elastic_ip_with_public_ipv4_returns_info():
    address = {
        "public_ip": "203.0.113.10"
    }

    result = evaluate_public_ip(address)

    assert result["check"] == "EIP_PUBLIC_IPV4"
    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_elastic_ip_without_public_ipv4_returns_warn():
    address = {
        "public_ip": None
    }

    result = evaluate_public_ip(address)

    assert result["check"] == "EIP_PUBLIC_IPV4"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_required_tags_present_returns_pass():
    address = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(address)

    assert result["check"] == "EIP_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    address = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(address)

    assert result["check"] == "EIP_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_address_returns_three_findings():
    address = {
        "associated": False,
        "public_ip": "203.0.113.10",
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    results = evaluate_address(address)

    assert len(results) == 3
    assert results[0]["status"] == "WARN"
    assert results[1]["status"] == "INFO"
    assert results[2]["status"] == "PASS"
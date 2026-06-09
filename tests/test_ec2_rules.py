from app.scanner.ec2_rules import (
evaluate_public_ip,
evaluate_instance_state,
evaluate_tags,
evaluate_monitoring,
evaluate_instance,
)

def test_running_instance_state_returns_warn():
    instance = {
        "state": "running"
    }


    result = evaluate_instance_state(instance)

    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_stopped_instance_state_returns_warn():
    instance = {
        "state": "stopped"
    }


    result = evaluate_instance_state(instance)

    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_terminated_instance_state_returns_pass():
    instance = {
        "state": "terminated"
    }


    result = evaluate_instance_state(instance)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_active_instance_with_public_ip_returns_warn():
    instance = {
        "state": "running",
        "has_public_ip": True
    }


    result = evaluate_public_ip(instance)

    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_active_instance_without_public_ip_returns_pass():
    instance = {
        "state": "running",
        "has_public_ip": False
    }


    result = evaluate_public_ip(instance)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_terminated_instance_with_old_public_ip_returns_pass():
    instance = {
        "state": "terminated",
        "has_public_ip": True
    }


    result = evaluate_public_ip(instance)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_required_tags_present_returns_pass():
    instance = {
        "tags": {
        "Project": "AWSFreeTierGuardian",
        "Environment": "Dev",
    }
}


    result = evaluate_tags(instance)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    instance = {
        "tags": {
        "Project": "AWSFreeTierGuardian"
    }
}


    result = evaluate_tags(instance)

    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_detailed_monitoring_disabled_returns_pass():
    instance = {
        "monitoring_state": "disabled"
    }


    result = evaluate_monitoring(instance)

    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_detailed_monitoring_enabled_returns_info():
    instance = {
        "monitoring_state": "enabled"
    }


    result = evaluate_monitoring(instance)

    assert result["status"] == "INFO"
    assert result["severity"] == "LOW"


def test_evaluate_instance_returns_four_findings():
    instance = {
        "state": "running",
        "has_public_ip": False,
        "monitoring_state": "disabled",
        "tags": {
        "Project": "AWSFreeTierGuardian",
        "Environment": "Dev",
    },
}


    results = evaluate_instance(instance)

    assert len(results) == 4
    assert results[0]["status"] == "PASS"
    assert results[1]["status"] == "WARN"
    assert results[2]["status"] == "PASS"
    assert results[3]["status"] == "PASS"


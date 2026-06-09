from app.scanner.ebs_rules import (
    evaluate_volume_state,
    evaluate_encryption,
    evaluate_delete_on_termination,
    evaluate_tags,
    evaluate_volume_size,
    evaluate_volume,
)


def test_available_unattached_volume_returns_warn():
    volume = {
        "state": "available"
    }

    result = evaluate_volume_state(volume)

    assert result["check"] == "EBS_VOLUME_UNATTACHED"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_in_use_volume_returns_pass():
    volume = {
        "state": "in-use"
    }

    result = evaluate_volume_state(volume)

    assert result["check"] == "EBS_VOLUME_ATTACHED"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_encrypted_volume_returns_pass():
    volume = {
        "encrypted": True
    }

    result = evaluate_encryption(volume)

    assert result["check"] == "EBS_ENCRYPTION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_unencrypted_volume_returns_fail():
    volume = {
        "encrypted": False
    }

    result = evaluate_encryption(volume)

    assert result["check"] == "EBS_ENCRYPTION"
    assert result["status"] == "FAIL"
    assert result["severity"] == "HIGH"


def test_attached_volume_delete_on_termination_true_returns_pass():
    volume = {
        "attachments": [
            {
                "delete_on_termination": True
            }
        ]
    }

    result = evaluate_delete_on_termination(volume)

    assert result["check"] == "EBS_DELETE_ON_TERMINATION"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_unattached_volume_delete_on_termination_returns_warn():
    volume = {
        "attachments": []
    }

    result = evaluate_delete_on_termination(volume)

    assert result["check"] == "EBS_DELETE_ON_TERMINATION"
    assert result["status"] == "WARN"
    assert result["severity"] == "MEDIUM"


def test_required_tags_present_returns_pass():
    volume = {
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        }
    }

    result = evaluate_tags(volume)

    assert result["check"] == "EBS_REQUIRED_TAGS"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_missing_required_tags_returns_warn():
    volume = {
        "tags": {
            "Project": "AWSFreeTierGuardian"
        }
    }

    result = evaluate_tags(volume)

    assert result["check"] == "EBS_REQUIRED_TAGS"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_small_volume_size_returns_pass():
    volume = {
        "size_gib": 8
    }

    result = evaluate_volume_size(volume)

    assert result["check"] == "EBS_VOLUME_SIZE"
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_large_volume_size_returns_warn():
    volume = {
        "size_gib": 100
    }

    result = evaluate_volume_size(volume)

    assert result["check"] == "EBS_VOLUME_SIZE"
    assert result["status"] == "WARN"
    assert result["severity"] == "LOW"


def test_evaluate_volume_returns_five_findings():
    volume = {
        "state": "available",
        "encrypted": True,
        "attachments": [],
        "tags": {
            "Project": "AWSFreeTierGuardian",
            "Environment": "Dev",
        },
        "size_gib": 8,
    }

    results = evaluate_volume(volume)

    assert len(results) == 5
    assert results[0]["status"] == "WARN"
    assert results[1]["status"] == "PASS"
    assert results[2]["status"] == "WARN"
    assert results[3]["status"] == "PASS"
    assert results[4]["status"] == "PASS"
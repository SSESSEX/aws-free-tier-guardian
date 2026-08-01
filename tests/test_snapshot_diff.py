import pytest

from app.snapshots.diff import diff_resources


def test_diff_resources_detects_added_resource():
    previous = [
        {"resource_id": "bucket-a", "public": False},
    ]

    current = [
        {"resource_id": "bucket-a", "public": False},
        {"resource_id": "bucket-b", "public": False},
    ]

    result = diff_resources(previous, current)

    assert result["summary"]["added_count"] == 1
    assert result["summary"]["removed_count"] == 0
    assert result["summary"]["changed_count"] == 0
    assert result["added"][0]["resource_id"] == "bucket-b"


def test_diff_resources_detects_removed_resource():
    previous = [
        {"resource_id": "bucket-a", "public": False},
        {"resource_id": "bucket-b", "public": False},
    ]

    current = [
        {"resource_id": "bucket-a", "public": False},
    ]

    result = diff_resources(previous, current)

    assert result["summary"]["added_count"] == 0
    assert result["summary"]["removed_count"] == 1
    assert result["summary"]["changed_count"] == 0
    assert result["removed"][0]["resource_id"] == "bucket-b"


def test_diff_resources_detects_changed_resource():
    previous = [
        {"resource_id": "bucket-a", "public": False, "encryption": "AES256"},
    ]

    current = [
        {"resource_id": "bucket-a", "public": True, "encryption": "AES256"},
    ]

    result = diff_resources(previous, current)

    assert result["summary"]["changed_count"] == 1
    assert result["changed"][0].resource_id == "bucket-a"
    assert result["changed"][0].changed_fields == ["public"]


def test_diff_resources_detects_unchanged_resource():
    previous = [
        {"resource_id": "bucket-a", "public": False},
    ]

    current = [
        {"resource_id": "bucket-a", "public": False},
    ]

    result = diff_resources(previous, current)

    assert result["summary"]["unchanged_count"] == 1
    assert result["summary"]["changed_count"] == 0


def test_diff_resources_can_ignore_collection_metadata():
    previous = [
        {
            "resource_id": "bucket-a",
            "public": False,
            "collected_at": "2026-08-01T10:00:00Z",
        },
    ]

    current = [
        {
            "resource_id": "bucket-a",
            "public": False,
            "collected_at": "2026-08-01T11:00:00Z",
        },
    ]

    result = diff_resources(
        previous,
        current,
        ignore_fields={"collected_at"},
    )

    assert result["summary"]["changed_count"] == 0
    assert result["summary"]["unchanged_count"] == 1


def test_diff_resources_rejects_missing_resource_id():
    previous = [
        {"public": False},
    ]

    current = []

    with pytest.raises(ValueError, match="resource_id"):
        diff_resources(previous, current)


def test_diff_resources_rejects_duplicate_resource_ids():
    previous = [
        {"resource_id": "bucket-a", "public": False},
        {"resource_id": "bucket-a", "public": True},
    ]

    current = []

    with pytest.raises(ValueError, match="Duplicate resource id"):
        diff_resources(previous, current)
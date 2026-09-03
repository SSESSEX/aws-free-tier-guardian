import json
from datetime import datetime, timezone

import pytest

from app.snapshots.diff import diff_resources
from app.snapshots.report import (
    build_snapshot_diff_json_document,
    create_latest_snapshot_diff_report,
    render_snapshot_diff_markdown,
    write_snapshot_diff_json_report,
    write_snapshot_diff_report,
)
from app.snapshots.store import build_snapshot_document, save_snapshot


def test_render_snapshot_diff_markdown_includes_summary_counts():
    previous_snapshot = build_snapshot_document(
        [{"resource_id": "bucket-a", "public": False}],
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    current_snapshot = build_snapshot_document(
        [
            {"resource_id": "bucket-a", "public": True},
            {"resource_id": "bucket-b", "public": False},
        ],
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )

    diff_result = diff_resources(
        previous_snapshot["resources"],
        current_snapshot["resources"],
    )

    markdown = render_snapshot_diff_markdown(
        previous_snapshot,
        current_snapshot,
        diff_result,
    )

    assert "# Snapshot Diff Report" in markdown
    assert "| Added resources | 1 |" in markdown
    assert "| Changed resources | 1 |" in markdown
    assert "`bucket-a` changed fields: `public`" in markdown
    assert "`bucket-b`" in markdown


def test_write_snapshot_diff_report_creates_markdown_file(tmp_path):
    previous_snapshot = build_snapshot_document(
        [{"resource_id": "bucket-a", "public": False}],
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    current_snapshot = build_snapshot_document(
        [{"resource_id": "bucket-a", "public": True}],
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )

    diff_result = diff_resources(
        previous_snapshot["resources"],
        current_snapshot["resources"],
    )

    report_path = write_snapshot_diff_report(
        previous_snapshot,
        current_snapshot,
        diff_result,
        report_dir=tmp_path,
    )

    assert report_path.exists()
    assert report_path.name == "aws-config-20260801T110000Z-diff.md"

    content = report_path.read_text(encoding="utf-8")

    assert "# Snapshot Diff Report" in content
    assert "`bucket-a` changed fields: `public`" in content


def test_build_snapshot_diff_json_document_creates_deterministic_change_events():
    previous_snapshot = build_snapshot_document(
        [
            {"resource_id": "resource-d", "value": "same"},
            {"resource_id": "resource-c", "value": "before"},
            {"resource_id": "resource-b", "value": "removed"},
        ],
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    current_snapshot = build_snapshot_document(
        [
            {"resource_id": "resource-d", "value": "same"},
            {"resource_id": "resource-c", "value": "after"},
            {"resource_id": "resource-a", "value": "added"},
        ],
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )
    diff_result = diff_resources(
        previous_snapshot["resources"], current_snapshot["resources"]
    )

    document = build_snapshot_diff_json_document(
        previous_snapshot, current_snapshot, diff_result
    )

    assert document["schema_version"] == "1.0"
    assert document["key_field"] == "resource_id"
    assert document["previous_snapshot"] == {
        "snapshot_id": "aws-config-20260801T100000Z",
        "collected_at": "2026-08-01T10:00:00Z",
    }
    assert document["current_snapshot"] == {
        "snapshot_id": "aws-config-20260801T110000Z",
        "collected_at": "2026-08-01T11:00:00Z",
    }
    assert document["summary"] == {
        "previous_count": 3,
        "current_count": 3,
        "added_count": 1,
        "removed_count": 1,
        "changed_count": 1,
        "unchanged_count": 1,
    }
    assert [change["resource_id"] for change in document["changes"]] == [
        "resource-a",
        "resource-b",
        "resource-c",
    ]
    assert document["changes"] == [
        {
            "change_type": "added",
            "resource_id": "resource-a",
            "changed_fields": [],
            "before": None,
            "after": {"resource_id": "resource-a", "value": "added"},
        },
        {
            "change_type": "removed",
            "resource_id": "resource-b",
            "changed_fields": [],
            "before": {"resource_id": "resource-b", "value": "removed"},
            "after": None,
        },
        {
            "change_type": "changed",
            "resource_id": "resource-c",
            "changed_fields": ["value"],
            "before": {"resource_id": "resource-c", "value": "before"},
            "after": {"resource_id": "resource-c", "value": "after"},
        },
    ]
    assert "resource-d" not in json.dumps(document["changes"])


def test_write_snapshot_diff_json_report_is_parseable_and_ends_with_newline(tmp_path):
    previous_snapshot = build_snapshot_document(
        [{"resource_id": "bucket-a", "public": False}],
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    current_snapshot = build_snapshot_document(
        [{"resource_id": "bucket-a", "public": True}],
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )
    diff_result = diff_resources(
        previous_snapshot["resources"], current_snapshot["resources"]
    )

    report_path = write_snapshot_diff_json_report(
        previous_snapshot, current_snapshot, diff_result, report_dir=tmp_path
    )

    assert report_path.name == "aws-config-20260801T110000Z-diff.json"
    assert report_path.read_bytes().endswith(b"\n")
    assert not list(tmp_path.glob("*.tmp"))
    parsed = json.loads(report_path.read_text(encoding="utf-8"))
    assert parsed["changes"][0]["changed_fields"] == ["public"]


def test_json_diff_supports_a_custom_resource_key():
    previous_snapshot = build_snapshot_document(
        [{"name": "bucket-a", "public": False}],
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    current_snapshot = build_snapshot_document(
        [{"name": "bucket-a", "public": True}],
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )
    diff_result = diff_resources(
        previous_snapshot["resources"],
        current_snapshot["resources"],
        key_field="name",
    )

    document = build_snapshot_diff_json_document(
        previous_snapshot, current_snapshot, diff_result, key_field="name"
    )

    assert document["key_field"] == "name"
    assert document["changes"][0]["resource_id"] == "bucket-a"


def test_json_diff_rejects_invalid_changed_entry():
    previous_snapshot = build_snapshot_document([])
    current_snapshot = build_snapshot_document([])
    diff_result = {
        "summary": {},
        "added": [],
        "removed": [],
        "changed": [{"resource_id": "not-a-resource-change"}],
    }

    with pytest.raises(ValueError, match="ResourceChange"):
        build_snapshot_diff_json_document(
            previous_snapshot, current_snapshot, diff_result
        )


@pytest.mark.parametrize("snapshot_id", ["../outside", "nested/report", "bad\\name"])
def test_diff_writers_reject_unsafe_snapshot_ids(tmp_path, snapshot_id):
    previous_snapshot = build_snapshot_document([])
    current_snapshot = build_snapshot_document([])
    current_snapshot["snapshot_id"] = snapshot_id
    diff_result = diff_resources([], [])

    with pytest.raises(ValueError, match="snapshot_id"):
        write_snapshot_diff_report(
            previous_snapshot, current_snapshot, diff_result, report_dir=tmp_path
        )
    with pytest.raises(ValueError, match="snapshot_id"):
        write_snapshot_diff_json_report(
            previous_snapshot, current_snapshot, diff_result, report_dir=tmp_path
        )

    assert list(tmp_path.iterdir()) == []


def test_create_latest_snapshot_diff_report_uses_latest_two_snapshots(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "reports"

    save_snapshot(
        [{"resource_id": "bucket-a", "public": False}],
        snapshot_dir=snapshot_dir,
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    save_snapshot(
        [
            {"resource_id": "bucket-a", "public": True},
            {"resource_id": "bucket-b", "public": False},
        ],
        snapshot_dir=snapshot_dir,
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )

    result = create_latest_snapshot_diff_report(
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
    )

    assert result is not None
    assert result.summary["previous_count"] == 1
    assert result.summary["current_count"] == 2
    assert result.summary["added_count"] == 1
    assert result.summary["changed_count"] == 1
    assert result.report_path.exists()
    assert result.json_report_path.exists()

    content = result.report_path.read_text(encoding="utf-8")

    assert "`bucket-a` changed fields: `public`" in content
    assert "`bucket-b`" in content

    json_content = json.loads(result.json_report_path.read_text(encoding="utf-8"))
    assert json_content["summary"] == result.summary
    assert {change["resource_id"] for change in json_content["changes"]} == {
        "bucket-a",
        "bucket-b",
    }


def test_create_latest_snapshot_diff_report_returns_none_with_fewer_than_two_snapshots(
    tmp_path,
):
    result = create_latest_snapshot_diff_report(
        snapshot_dir=tmp_path / "snapshots",
        report_dir=tmp_path / "reports",
    )

    assert result is None

    save_snapshot(
        [{"resource_id": "bucket-a", "public": False}],
        snapshot_dir=tmp_path / "snapshots",
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    result = create_latest_snapshot_diff_report(
        snapshot_dir=tmp_path / "snapshots",
        report_dir=tmp_path / "reports",
    )

    assert result is None

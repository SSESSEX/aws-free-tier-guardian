from datetime import datetime, timezone

from app.snapshots.diff import diff_resources
from app.snapshots.report import (
    create_latest_snapshot_diff_report,
    render_snapshot_diff_markdown,
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

    content = result.report_path.read_text(encoding="utf-8")

    assert "`bucket-a` changed fields: `public`" in content
    assert "`bucket-b`" in content


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
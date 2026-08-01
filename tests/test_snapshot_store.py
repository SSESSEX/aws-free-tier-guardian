from datetime import datetime, timezone

import pytest

from app.snapshots.store import (
    build_snapshot_document,
    get_latest_snapshot_path,
    get_previous_snapshot_path,
    list_snapshot_paths,
    load_snapshot,
    save_snapshot,
)


def test_build_snapshot_document_adds_metadata_and_resource_count():
    collected_at = datetime(2026, 8, 1, 23, 25, 0, tzinfo=timezone.utc)

    snapshot = build_snapshot_document(
        [{"resource_id": "bucket-a", "public": False}],
        snapshot_name="aws-config",
        collected_at=collected_at,
        metadata={"source": "unit-test"},
    )

    assert snapshot["schema_version"] == "1.0"
    assert snapshot["snapshot_id"] == "aws-config-20260801T232500Z"
    assert snapshot["snapshot_name"] == "aws-config"
    assert snapshot["collected_at"] == "2026-08-01T23:25:00Z"
    assert snapshot["resource_count"] == 1
    assert snapshot["metadata"] == {"source": "unit-test"}
    assert snapshot["resources"] == [{"resource_id": "bucket-a", "public": False}]


def test_save_snapshot_creates_timestamped_json_file(tmp_path):
    collected_at = datetime(2026, 8, 1, 23, 25, 0, tzinfo=timezone.utc)

    snapshot_path = save_snapshot(
        [{"resource_id": "bucket-a", "public": False}],
        snapshot_dir=tmp_path,
        snapshot_name="aws-config",
        collected_at=collected_at,
    )

    assert snapshot_path.exists()
    assert snapshot_path.name == "aws-config-20260801T232500Z.json"


def test_load_snapshot_reads_saved_snapshot(tmp_path):
    collected_at = datetime(2026, 8, 1, 23, 25, 0, tzinfo=timezone.utc)

    snapshot_path = save_snapshot(
        [{"resource_id": "bucket-a", "public": False}],
        snapshot_dir=tmp_path,
        collected_at=collected_at,
    )

    loaded = load_snapshot(snapshot_path)

    assert loaded["snapshot_id"] == "aws-config-20260801T232500Z"
    assert loaded["resources"] == [{"resource_id": "bucket-a", "public": False}]


def test_list_snapshot_paths_returns_files_in_chronological_order(tmp_path):
    save_snapshot(
        [{"resource_id": "bucket-b"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )

    save_snapshot(
        [{"resource_id": "bucket-a"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    paths = list_snapshot_paths(tmp_path)

    assert [path.name for path in paths] == [
        "aws-config-20260801T100000Z.json",
        "aws-config-20260801T110000Z.json",
    ]


def test_get_latest_snapshot_path_returns_latest_file(tmp_path):
    save_snapshot(
        [{"resource_id": "bucket-a"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    save_snapshot(
        [{"resource_id": "bucket-b"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )

    latest = get_latest_snapshot_path(tmp_path)

    assert latest is not None
    assert latest.name == "aws-config-20260801T110000Z.json"


def test_get_previous_snapshot_path_returns_snapshot_before_latest(tmp_path):
    save_snapshot(
        [{"resource_id": "bucket-a"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    save_snapshot(
        [{"resource_id": "bucket-b"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc),
    )

    save_snapshot(
        [{"resource_id": "bucket-c"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    previous = get_previous_snapshot_path(tmp_path)

    assert previous is not None
    assert previous.name == "aws-config-20260801T110000Z.json"


def test_latest_and_previous_return_none_when_unavailable(tmp_path):
    assert get_latest_snapshot_path(tmp_path) is None
    assert get_previous_snapshot_path(tmp_path) is None

    save_snapshot(
        [{"resource_id": "bucket-a"}],
        snapshot_dir=tmp_path,
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert get_latest_snapshot_path(tmp_path) is not None
    assert get_previous_snapshot_path(tmp_path) is None


def test_snapshot_name_is_normalised_for_filename(tmp_path):
    snapshot_path = save_snapshot(
        [{"resource_id": "bucket-a"}],
        snapshot_dir=tmp_path,
        snapshot_name="AWS Config Snapshot",
        collected_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert snapshot_path.name == "aws-config-snapshot-20260801T100000Z.json"


def test_save_snapshot_rejects_non_list_resources(tmp_path):
    with pytest.raises(ValueError, match="resources must be a list"):
        save_snapshot(
            {"resource_id": "bucket-a"},  # type: ignore[arg-type]
            snapshot_dir=tmp_path,
        )


def test_save_snapshot_rejects_non_dict_resource_items(tmp_path):
    with pytest.raises(ValueError, match="Every resource must be a dictionary"):
        save_snapshot(
            ["bucket-a"],  # type: ignore[list-item]
            snapshot_dir=tmp_path,
        )


def test_save_snapshot_rejects_invalid_metadata(tmp_path):
    with pytest.raises(ValueError, match="metadata must be a dictionary"):
        save_snapshot(
            [{"resource_id": "bucket-a"}],
            snapshot_dir=tmp_path,
            metadata=["not-a-dict"],  # type: ignore[arg-type]
        )
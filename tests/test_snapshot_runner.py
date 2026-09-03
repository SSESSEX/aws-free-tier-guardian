import json
from datetime import datetime, timezone

import pytest

from app.snapshots.runner import (
    create_snapshot_from_json_file,
    load_resources_from_json_file,
    main,
)


def test_load_resources_from_plain_list_json(tmp_path):
    input_path = tmp_path / "resources.json"
    input_path.write_text(
        json.dumps(
            [
                {"resource_id": "bucket-a", "public": False},
                {"resource_id": "bucket-b", "public": True},
            ]
        ),
        encoding="utf-8",
    )

    resources = load_resources_from_json_file(input_path)

    assert resources == [
        {"resource_id": "bucket-a", "public": False},
        {"resource_id": "bucket-b", "public": True},
    ]


def test_load_resources_from_snapshot_document_json(tmp_path):
    input_path = tmp_path / "snapshot.json"
    input_path.write_text(
        json.dumps(
            {
                "snapshot_id": "example",
                "resources": [
                    {"resource_id": "bucket-a", "public": False},
                ],
            }
        ),
        encoding="utf-8",
    )

    resources = load_resources_from_json_file(input_path)

    assert resources == [{"resource_id": "bucket-a", "public": False}]


def test_load_resources_rejects_unsupported_json_shape(tmp_path):
    input_path = tmp_path / "invalid.json"
    input_path.write_text(
        json.dumps({"not_resources": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="top-level 'resources' list"):
        load_resources_from_json_file(input_path)


def test_load_resources_rejects_non_dict_resource_items(tmp_path):
    input_path = tmp_path / "invalid.json"
    input_path.write_text(
        json.dumps(["bucket-a"]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Every resource"):
        load_resources_from_json_file(input_path)


def test_create_snapshot_from_json_file_saves_first_snapshot_without_report(tmp_path):
    input_path = tmp_path / "resources.json"
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "reports"

    input_path.write_text(
        json.dumps([{"resource_id": "bucket-a", "public": False}]),
        encoding="utf-8",
    )

    result = create_snapshot_from_json_file(
        input_path,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        collected_at=datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert result.snapshot_path.exists()
    assert result.snapshot_path.name == "aws-config-20260803T100000Z.json"
    assert result.diff_report is None


def test_create_snapshot_from_json_file_writes_report_when_previous_snapshot_exists(
    tmp_path,
):
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "reports"

    first_input = tmp_path / "first.json"
    first_input.write_text(
        json.dumps([{"resource_id": "bucket-a", "public": False}]),
        encoding="utf-8",
    )

    create_snapshot_from_json_file(
        first_input,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        collected_at=datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc),
    )

    second_input = tmp_path / "second.json"
    second_input.write_text(
        json.dumps(
            [
                {"resource_id": "bucket-a", "public": True},
                {"resource_id": "bucket-b", "public": False},
            ]
        ),
        encoding="utf-8",
    )

    result = create_snapshot_from_json_file(
        second_input,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        collected_at=datetime(2026, 8, 3, 11, 0, 0, tzinfo=timezone.utc),
    )

    assert result.snapshot_path.exists()
    assert result.diff_report is not None
    assert result.diff_report.summary["added_count"] == 1
    assert result.diff_report.summary["changed_count"] == 1
    assert result.diff_report.report_path.exists()
    assert result.diff_report.json_report_path.exists()

    report_content = result.diff_report.report_path.read_text(encoding="utf-8")

    assert "`bucket-a` changed fields: `public`" in report_content
    assert "`bucket-b`" in report_content

    json_report = json.loads(
        result.diff_report.json_report_path.read_text(encoding="utf-8")
    )
    assert {change["resource_id"] for change in json_report["changes"]} == {
        "bucket-a",
        "bucket-b",
    }


def test_main_saves_snapshot_from_cli_args(tmp_path):
    input_path = tmp_path / "resources.json"
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "reports"

    input_path.write_text(
        json.dumps([{"resource_id": "bucket-a", "public": False}]),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--report-dir",
            str(report_dir),
        ]
    )

    assert exit_code == 0
    assert list(snapshot_dir.glob("aws-config-*.json"))

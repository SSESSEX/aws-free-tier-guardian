import json
from datetime import datetime, timezone

import pytest

from app.snapshots.guardian_report import (
    create_snapshot_from_guardian_report_file,
    extract_guardian_snapshot_resources,
    load_guardian_report,
    main,
)


def _sample_guardian_report(public_bucket: bool = False):
    return {
        "scan_time": "2026-08-03T18:00:00Z",
        "aws_profile": "guardian-dev",
        "aws_region": "eu-west-2",
        "summary": {
            "overall_status": "WARN",
            "services_scanned": 2,
            "resources_scanned": 2,
        },
        "services": {
            "s3": {
                "bucket_count": 1,
                "summary": {
                    "total_findings": 1,
                    "warnings": 1 if public_bucket else 0,
                    "overall_status": "WARN" if public_bucket else "PASS",
                },
                "buckets": [
                    {
                        "name": "example-bucket",
                        "region": "eu-west-2",
                        "public_access_block": {
                            "block_public_acls": not public_bucket,
                        },
                        "findings": [],
                    }
                ],
            },
            "iam_access_keys": {
                "access_key_count": 1,
                "summary": {
                    "total_access_keys": 1,
                    "active_keys": 1,
                    "overall_status": "PASS",
                },
                "access_keys": [
                    {
                        "user_name": "guardian-dev",
                        "masked_access_key_id": "ABCD****1234",
                        "status": "Active",
                        "findings": [],
                    }
                ],
            },
        },
    }


def test_load_guardian_report_reads_json_object(tmp_path):
    report_path = tmp_path / "guardian.json"
    report_path.write_text(
        json.dumps(_sample_guardian_report()),
        encoding="utf-8",
    )

    loaded = load_guardian_report(report_path)

    assert loaded["aws_region"] == "eu-west-2"


def test_extract_guardian_snapshot_resources_flattens_service_summaries_and_resources():
    resources = extract_guardian_snapshot_resources(_sample_guardian_report())

    resource_ids = {resource["resource_id"] for resource in resources}

    assert "iam_access_keys:service_summary:summary" in resource_ids
    assert "iam_access_keys:access_key:guardian-dev/ABCD****1234" in resource_ids
    assert "s3:service_summary:summary" in resource_ids
    assert "s3:bucket:example-bucket" in resource_ids

    assert len(resources) == 4


def test_extract_guardian_snapshot_resources_rejects_missing_services():
    with pytest.raises(ValueError, match="top-level 'services'"):
        extract_guardian_snapshot_resources({"summary": {}})


def test_create_snapshot_from_guardian_report_file_saves_first_snapshot_without_report(
    tmp_path,
):
    report_path = tmp_path / "guardian.json"
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"

    report_path.write_text(
        json.dumps(_sample_guardian_report()),
        encoding="utf-8",
    )

    result = create_snapshot_from_guardian_report_file(
        report_path,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        collected_at=datetime(2026, 8, 3, 18, 0, 0, tzinfo=timezone.utc),
    )

    assert result.snapshot_path.exists()
    assert result.snapshot_path.name == "aws-config-20260803T180000Z.json"
    assert result.resource_count == 4
    assert result.diff_report is None


def test_create_snapshot_from_guardian_report_file_writes_diff_on_second_snapshot(
    tmp_path,
):
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"

    first_report_path = tmp_path / "guardian-first.json"
    first_report_path.write_text(
        json.dumps(_sample_guardian_report(public_bucket=False)),
        encoding="utf-8",
    )

    create_snapshot_from_guardian_report_file(
        first_report_path,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        collected_at=datetime(2026, 8, 3, 18, 0, 0, tzinfo=timezone.utc),
    )

    second_report_path = tmp_path / "guardian-second.json"
    second_report_path.write_text(
        json.dumps(_sample_guardian_report(public_bucket=True)),
        encoding="utf-8",
    )

    result = create_snapshot_from_guardian_report_file(
        second_report_path,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        collected_at=datetime(2026, 8, 3, 19, 0, 0, tzinfo=timezone.utc),
    )

    assert result.diff_report is not None
    assert result.diff_report.summary["changed_count"] == 2

    report_content = result.diff_report.report_path.read_text(encoding="utf-8")

    assert "`s3:bucket:example-bucket` changed fields: `configuration`" in report_content
    assert "`s3:service_summary:summary` changed fields: `configuration`" in report_content


def test_main_creates_snapshot_from_cli_args(tmp_path):
    report_path = tmp_path / "guardian.json"
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"

    report_path.write_text(
        json.dumps(_sample_guardian_report()),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--input",
            str(report_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--report-dir",
            str(report_dir),
        ]
    )

    assert exit_code == 0
    assert list(snapshot_dir.glob("aws-config-*.json"))
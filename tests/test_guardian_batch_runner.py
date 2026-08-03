import json
import subprocess
from datetime import datetime, timezone

import pytest

from app.snapshots.guardian_report import create_snapshot_from_guardian_report_file
from app.snapshots.run_guardian_batch import main, run_guardian_batch


def _write_sample_guardian_report(path, *, public_bucket=False):
    path.write_text(
        json.dumps(
            {
                "scan_time": "2026-08-03T18:00:00Z",
                "aws_profile": "guardian-dev",
                "aws_region": "eu-west-2",
                "summary": {
                    "overall_status": "WARN",
                    "services_scanned": 1,
                    "resources_scanned": 1,
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
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_run_guardian_batch_runs_scanner_then_creates_snapshot(
    tmp_path,
    monkeypatch,
):
    report_path = tmp_path / "aws_guardian_report.json"
    snapshot_dir = tmp_path / "snapshots"
    diff_report_dir = tmp_path / "diffs"

    def fake_run(*args, **kwargs):
        _write_sample_guardian_report(report_path)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="scanner ok",
            stderr="",
        )

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    result = run_guardian_batch(
        scanner_report_path=report_path,
        snapshot_dir=snapshot_dir,
        report_dir=diff_report_dir,
    )

    assert result.scanner_exit_code == 0
    assert result.scanner_report_path == report_path
    assert result.snapshot_result.snapshot_path.exists()
    assert result.snapshot_result.resource_count == 2
    assert result.snapshot_result.diff_report is None


def test_run_guardian_batch_creates_diff_when_previous_snapshot_exists(
    tmp_path,
    monkeypatch,
):
    report_path = tmp_path / "aws_guardian_report.json"
    snapshot_dir = tmp_path / "snapshots"
    diff_report_dir = tmp_path / "diffs"

    _write_sample_guardian_report(report_path, public_bucket=False)

    create_snapshot_from_guardian_report_file(
        report_path,
        snapshot_dir=snapshot_dir,
        report_dir=diff_report_dir,
        collected_at=datetime(2026, 8, 3, 18, 0, 0, tzinfo=timezone.utc),
    )

    def fake_run(*args, **kwargs):
        _write_sample_guardian_report(report_path, public_bucket=True)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="scanner ok",
            stderr="",
        )

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    result = run_guardian_batch(
        scanner_report_path=report_path,
        snapshot_dir=snapshot_dir,
        report_dir=diff_report_dir,
    )

    assert result.snapshot_result.diff_report is not None
    assert result.snapshot_result.diff_report.summary["changed_count"] == 2
    assert result.snapshot_result.diff_report.report_path.exists()


def test_run_guardian_batch_raises_when_scanner_fails(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="scanner output",
            stderr="scanner error",
        )

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Guardian scanner failed"):
        run_guardian_batch(
            scanner_report_path=tmp_path / "missing.json",
            snapshot_dir=tmp_path / "snapshots",
            report_dir=tmp_path / "diffs",
        )


def test_run_guardian_batch_raises_when_report_is_missing(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="scanner ok",
            stderr="",
        )

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    with pytest.raises(FileNotFoundError, match="expected JSON report"):
        run_guardian_batch(
            scanner_report_path=tmp_path / "missing.json",
            snapshot_dir=tmp_path / "snapshots",
            report_dir=tmp_path / "diffs",
        )


def test_main_returns_zero_for_successful_batch_run(tmp_path, monkeypatch):
    report_path = tmp_path / "aws_guardian_report.json"
    snapshot_dir = tmp_path / "snapshots"
    diff_report_dir = tmp_path / "diffs"

    def fake_run(*args, **kwargs):
        _write_sample_guardian_report(report_path)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="scanner ok",
            stderr="",
        )

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    exit_code = main(
        [
            "--scanner-report-path",
            str(report_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--report-dir",
            str(diff_report_dir),
        ]
    )

    assert exit_code == 0
    assert list(snapshot_dir.glob("aws-config-*.json"))
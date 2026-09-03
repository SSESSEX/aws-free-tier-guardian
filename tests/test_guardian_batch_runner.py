import json
import subprocess
from datetime import datetime, timezone

import pytest

from app.snapshots.guardian_report import create_snapshot_from_guardian_report_file
from app.snapshots.run_guardian_batch import (
    main,
    run_guardian_batch,
    run_guardian_scanner,
)


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


@pytest.mark.parametrize(
    ("write_db", "expected_command"),
    [
        (False, ["/example/python", "-m", "app.scanner.run_all"]),
        (
            True,
            ["/example/python", "-m", "app.scanner.run_all", "--write-db"],
        ),
    ],
)
def test_run_guardian_scanner_builds_expected_command(
    monkeypatch,
    write_db,
    expected_command,
):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "scanner ok", "")

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    run_guardian_scanner(
        python_executable="/example/python",
        write_db=write_db,
    )

    assert captured["command"] == expected_command
    assert captured["kwargs"] == {
        "check": False,
        "capture_output": True,
        "text": True,
    }


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


def test_main_write_db_flag_is_forwarded_to_scanner(tmp_path, monkeypatch):
    report_path = tmp_path / "aws_guardian_report.json"
    snapshot_dir = tmp_path / "snapshots"
    diff_report_dir = tmp_path / "diffs"
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        _write_sample_guardian_report(report_path)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="scanner ok",
            stderr="",
        )

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)

    exit_code = main(
        [
            "--write-db",
            "--scanner-report-path",
            str(report_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--report-dir",
            str(diff_report_dir),
        ]
    )

    assert exit_code == 0
    assert captured["command"][-1] == "--write-db"


def _seed_batch_history(tmp_path, monkeypatch, *, snapshot_name="aws-config"):
    report_path = tmp_path / "aws_guardian_report.json"
    snapshot_dir = tmp_path / "snapshots"
    report_dir = tmp_path / "diffs"
    _write_sample_guardian_report(report_path)

    for hour in (18, 19, 20):
        create_snapshot_from_guardian_report_file(
            report_path,
            snapshot_dir=snapshot_dir,
            report_dir=report_dir,
            snapshot_name=snapshot_name,
            collected_at=datetime(2026, 8, 3, hour, tzinfo=timezone.utc),
        )

    def create_at_fixed_time(*args, **kwargs):
        return create_snapshot_from_guardian_report_file(
            *args,
            **kwargs,
            collected_at=datetime(2026, 8, 3, 21, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.create_snapshot_from_guardian_report_file",
        create_at_fixed_time,
    )
    return report_path, snapshot_dir, report_dir


def test_batch_retention_is_disabled_by_default(tmp_path, monkeypatch):
    report_path, snapshot_dir, report_dir = _seed_batch_history(tmp_path, monkeypatch)

    def unexpected_cleanup(**kwargs):
        pytest.fail("retention must be explicitly enabled")

    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.prune_snapshot_history", unexpected_cleanup
    )
    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.run_guardian_scanner",
        lambda **kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    result = run_guardian_batch(
        scanner_report_path=report_path,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
    )

    assert result.retention_result is None
    assert len(list(snapshot_dir.glob("*.json"))) == 4
    assert len(list(report_dir.glob("*.md"))) == 3


def test_main_applies_retention_after_diff_and_forwards_options(
    tmp_path, monkeypatch, capsys
):
    from app.snapshots.retention import prune_snapshot_history

    report_path, snapshot_dir, report_dir = _seed_batch_history(
        tmp_path, monkeypatch, snapshot_name="Portfolio_Scan"
    )
    captured = {}

    def fake_run(command, **kwargs):
        captured["scanner_command"] = command
        return subprocess.CompletedProcess(command, 0, "", "")

    def checked_cleanup(**kwargs):
        # All four snapshots and the new diff must exist before cleanup starts.
        assert len(list(snapshot_dir.glob("*.json"))) == 4
        assert (report_dir / "portfolio-scan-20260803T210000Z-diff.md").is_file()
        captured["cleanup_options"] = kwargs
        return prune_snapshot_history(**kwargs)

    monkeypatch.setattr("app.snapshots.run_guardian_batch.subprocess.run", fake_run)
    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.prune_snapshot_history", checked_cleanup
    )

    exit_code = main(
        [
            "--write-db",
            "--retention-count", "2",
            "--snapshot-name", "Portfolio_Scan",
            "--scanner-report-path", str(report_path),
            "--snapshot-dir", str(snapshot_dir),
            "--report-dir", str(report_dir),
        ]
    )

    assert exit_code == 0
    assert captured["scanner_command"][-1] == "--write-db"
    assert "--retention-count" not in captured["scanner_command"]
    assert captured["cleanup_options"] == {
        "retention_count": 2,
        "snapshot_dir": str(snapshot_dir),
        "report_dir": str(report_dir),
        "snapshot_name": "Portfolio_Scan",
    }
    assert [path.name for path in sorted(snapshot_dir.iterdir())] == [
        "portfolio-scan-20260803T200000Z.json",
        "portfolio-scan-20260803T210000Z.json",
    ]
    assert [path.name for path in sorted(report_dir.iterdir())] == [
        "portfolio-scan-20260803T200000Z-diff.json",
        "portfolio-scan-20260803T200000Z-diff.md",
        "portfolio-scan-20260803T210000Z-diff.json",
        "portfolio-scan-20260803T210000Z-diff.md",
    ]
    output = capsys.readouterr().out
    assert "Diff report written:" in output
    assert "JSON diff report written:" in output
    assert (
        "Retention: kept at most 2 snapshots and 2 reports of each diff format"
        in output
    )
    assert (
        "deleted snapshots=2, markdown_diff_reports=1, json_diff_reports=1."
        in output
    )


def test_first_batch_with_retention_keeps_its_baseline(tmp_path, monkeypatch):
    report_path = tmp_path / "aws_guardian_report.json"
    _write_sample_guardian_report(report_path)
    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.run_guardian_scanner",
        lambda **kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    result = run_guardian_batch(
        scanner_report_path=report_path,
        snapshot_dir=tmp_path / "snapshots",
        report_dir=tmp_path / "diffs",
        retention_count=2,
    )

    assert result.snapshot_result.snapshot_path.is_file()
    assert result.snapshot_result.diff_report is None
    assert result.retention_result.deleted_snapshots == ()
    assert result.retention_result.deleted_reports == ()
    assert result.retention_result.deleted_json_reports == ()


@pytest.mark.parametrize("failure_stage", ["scanner", "missing-report", "snapshot", "diff"])
def test_batch_failures_never_prune_existing_history(
    tmp_path, monkeypatch, failure_stage
):
    report_path, snapshot_dir, report_dir = _seed_batch_history(tmp_path, monkeypatch)
    history = {
        path: path.read_bytes()
        for directory in (snapshot_dir, report_dir)
        for path in directory.iterdir()
    }

    def unexpected_cleanup(**kwargs):
        pytest.fail("cleanup must not run after a batch failure")

    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.prune_snapshot_history", unexpected_cleanup
    )
    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.run_guardian_scanner",
        lambda **kwargs: subprocess.CompletedProcess(
            [], 1 if failure_stage == "scanner" else 0, "", ""
        ),
    )

    def fail_artifact(*args, **kwargs):
        raise OSError(f"{failure_stage} write failed")

    if failure_stage == "missing-report":
        report_path.unlink()
    elif failure_stage == "snapshot":
        monkeypatch.setattr("app.snapshots.guardian_report.save_snapshot", fail_artifact)
    elif failure_stage == "diff":
        monkeypatch.setattr(
            "app.snapshots.guardian_report.create_latest_snapshot_diff_report",
            fail_artifact,
        )

    with pytest.raises((RuntimeError, FileNotFoundError, OSError)):
        run_guardian_batch(
            scanner_report_path=report_path,
            snapshot_dir=snapshot_dir,
            report_dir=report_dir,
            retention_count=2,
        )

    for path, contents in history.items():
        assert path.read_bytes() == contents


@pytest.mark.parametrize("retention_count", [0, 1, -1, True, 2.5, "2"])
def test_batch_rejects_invalid_retention_before_scanning(monkeypatch, retention_count):
    def unexpected_scanner(**kwargs):
        pytest.fail("invalid retention must fail before any AWS or database work")

    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.run_guardian_scanner", unexpected_scanner
    )

    with pytest.raises(ValueError, match="integer of at least 2"):
        run_guardian_batch(retention_count=retention_count)


@pytest.mark.parametrize("value", ["0", "1", "-1", "2.5", "invalid"])
def test_main_rejects_invalid_retention_arguments(monkeypatch, capsys, value):
    def unexpected_scanner(**kwargs):
        pytest.fail("invalid CLI input must not trigger a scan")

    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.run_guardian_scanner", unexpected_scanner
    )

    with pytest.raises(SystemExit) as exc_info:
        main(["--retention-count", value])

    assert exc_info.value.code == 2
    assert "retention count must be an integer of at least 2" in capsys.readouterr().err


def test_main_returns_failure_when_retention_fails(tmp_path, monkeypatch, capsys):
    report_path, snapshot_dir, report_dir = _seed_batch_history(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.run_guardian_scanner",
        lambda **kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    def fail_cleanup(**kwargs):
        raise PermissionError("retention cleanup denied")

    monkeypatch.setattr(
        "app.snapshots.run_guardian_batch.prune_snapshot_history", fail_cleanup
    )

    exit_code = main(
        [
            "--retention-count", "2",
            "--scanner-report-path", str(report_path),
            "--snapshot-dir", str(snapshot_dir),
            "--report-dir", str(report_dir),
        ]
    )

    assert exit_code == 1
    output = capsys.readouterr()
    assert "retention cleanup denied" in output.err
    assert "completed successfully" not in output.out
    assert len(list(snapshot_dir.glob("*.json"))) == 4
    assert len(list(report_dir.glob("*.md"))) == 3
    assert len(list(report_dir.glob("*-diff.json"))) == 3

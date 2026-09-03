"""Batch runner for AWS Free-Tier Guardian snapshot monitoring.

This module runs the Guardian scanner, converts the scanner JSON report into a
timestamped snapshot, and writes a diff report when a previous snapshot exists.

It is the first end-to-end batch automation entry point. PostgreSQL persistence
can be enabled explicitly and remains disabled by default:

scan -> report JSON -> optional PostgreSQL -> snapshot -> diff -> Markdown report
     -> optional retention cleanup
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.snapshots.guardian_report import (
    DEFAULT_GUARDIAN_REPORT_PATH,
    GuardianSnapshotResult,
    create_snapshot_from_guardian_report_file,
)
from app.snapshots.report import DEFAULT_DIFF_REPORT_DIR
from app.snapshots.retention import (
    SnapshotRetentionResult,
    prune_snapshot_history,
    validate_retention_count,
)
from app.snapshots.store import DEFAULT_SNAPSHOT_DIR, DEFAULT_SNAPSHOT_NAME


DEFAULT_SCANNER_MODULE = "app.scanner.run_all"


@dataclass(frozen=True)
class GuardianBatchRunResult:
    """Result from a full Guardian batch monitoring run."""

    scanner_exit_code: int
    scanner_report_path: Path
    snapshot_result: GuardianSnapshotResult
    retention_result: SnapshotRetentionResult | None = None


def run_guardian_scanner(
    *,
    scanner_module: str = DEFAULT_SCANNER_MODULE,
    python_executable: str = sys.executable,
    write_db: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run the Guardian scanner as a Python module."""

    command = [python_executable, "-m", scanner_module]

    if write_db:
        command.append("--write-db")

    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def run_guardian_batch(
    *,
    scanner_module: str = DEFAULT_SCANNER_MODULE,
    scanner_report_path: str | Path = DEFAULT_GUARDIAN_REPORT_PATH,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    python_executable: str = sys.executable,
    write_db: bool = False,
    retention_count: int | None = None,
) -> GuardianBatchRunResult:
    """Run the scanner and create a timestamped snapshot from its JSON report.

    When write_db is true, the scanner also persists its existing scan, resource,
    and finding records to PostgreSQL before snapshot processing continues.
    Retention is disabled unless a count is supplied, and runs only after
    snapshot and diff processing succeeds.
    """

    if retention_count is not None:
        validate_retention_count(retention_count)

    scanner_result = run_guardian_scanner(
        scanner_module=scanner_module,
        python_executable=python_executable,
        write_db=write_db,
    )

    if scanner_result.returncode != 0:
        raise RuntimeError(
            "Guardian scanner failed with exit code "
            f"{scanner_result.returncode}.\n\n"
            f"STDOUT:\n{scanner_result.stdout}\n\n"
            f"STDERR:\n{scanner_result.stderr}"
        )

    report_path = Path(scanner_report_path)

    if not report_path.exists():
        raise FileNotFoundError(
            "Guardian scanner completed successfully, but the expected JSON "
            f"report was not found: {report_path}"
        )

    snapshot_result = create_snapshot_from_guardian_report_file(
        report_path,
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        snapshot_name=snapshot_name,
    )

    retention_result = None
    if retention_count is not None:
        retention_result = prune_snapshot_history(
            retention_count=retention_count,
            snapshot_dir=snapshot_dir,
            report_dir=report_dir,
            snapshot_name=snapshot_name,
        )

    return GuardianBatchRunResult(
        scanner_exit_code=scanner_result.returncode,
        scanner_report_path=report_path,
        snapshot_result=snapshot_result,
        retention_result=retention_result,
    )


def _retention_count_arg(value: str) -> int:
    try:
        count = int(value)
        validate_retention_count(count)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "retention count must be an integer of at least 2"
        ) from exc

    return count


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run AWS Free-Tier Guardian as a batch monitoring loop: "
            "scan, snapshot, diff, and report."
        )
    )

    parser.add_argument(
        "--scanner-module",
        default=DEFAULT_SCANNER_MODULE,
        help="Python module used to run the Guardian scanner.",
    )

    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist scanner results to PostgreSQL before snapshot processing.",
    )

    parser.add_argument(
        "--retention-count",
        type=_retention_count_arg,
        metavar="N",
        help=(
            "After a successful run, permanently delete older generated files "
            "to keep at most N snapshots and N Markdown diffs (minimum 2). "
            "Disabled when omitted."
        ),
    )

    parser.add_argument(
        "--scanner-report-path",
        default=str(DEFAULT_GUARDIAN_REPORT_PATH),
        help="Expected JSON report path produced by the scanner.",
    )

    parser.add_argument(
        "--snapshot-dir",
        default=str(DEFAULT_SNAPSHOT_DIR),
        help="Directory where timestamped snapshots will be saved.",
    )

    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_DIFF_REPORT_DIR),
        help="Directory where snapshot diff reports will be written.",
    )

    parser.add_argument(
        "--snapshot-name",
        default=DEFAULT_SNAPSHOT_NAME,
        help="Logical snapshot name used as the filename prefix.",
    )

    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv or sys.argv[1:])

    try:
        result = run_guardian_batch(
            scanner_module=args.scanner_module,
            scanner_report_path=args.scanner_report_path,
            snapshot_dir=args.snapshot_dir,
            report_dir=args.report_dir,
            snapshot_name=args.snapshot_name,
            write_db=args.write_db,
            retention_count=args.retention_count,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    snapshot_result = result.snapshot_result

    print("Guardian batch run completed successfully.")
    print(f"Scanner report: {result.scanner_report_path}")
    print(
        "PostgreSQL persistence: "
        + ("enabled" if args.write_db else "skipped")
    )
    print(f"Snapshot saved: {snapshot_result.snapshot_path}")
    print(f"Snapshot resources: {snapshot_result.resource_count}")

    if snapshot_result.diff_report is None:
        print("Diff report skipped: fewer than two snapshots are available.")
    else:
        print(f"Diff report written: {snapshot_result.diff_report.report_path}")

    if result.retention_result is not None:
        print(
            f"Retention: kept at most {args.retention_count} snapshots and "
            f"{args.retention_count} diff reports; deleted "
            f"snapshots={len(result.retention_result.deleted_snapshots)}, "
            f"diff_reports={len(result.retention_result.deleted_reports)}."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

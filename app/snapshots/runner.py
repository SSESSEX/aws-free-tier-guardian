"""Snapshot runner utilities.

This module provides a small bridge between JSON scanner output and the
snapshot/diff/report system.

It reads a JSON file containing resources, saves a timestamped snapshot, and
creates a diff report when at least two snapshots are available.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from app.snapshots.report import DEFAULT_DIFF_REPORT_DIR, SnapshotDiffReport
from app.snapshots.report import create_latest_snapshot_diff_report
from app.snapshots.store import (
    DEFAULT_SNAPSHOT_DIR,
    DEFAULT_SNAPSHOT_NAME,
    SnapshotResource,
    save_snapshot,
)


@dataclass(frozen=True)
class SnapshotRunResult:
    """Result from saving a snapshot and optionally creating a diff report."""

    snapshot_path: Path
    diff_report: SnapshotDiffReport | None


def load_resources_from_json_file(input_path: str | Path) -> list[SnapshotResource]:
    """Load resources from a JSON file.

    Supported input shapes:

    1. A direct list of resource dictionaries.
    2. A document containing a top-level "resources" list.
    """

    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input JSON file does not exist: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        resources = payload
    elif isinstance(payload, dict) and isinstance(payload.get("resources"), list):
        resources = payload["resources"]
    else:
        raise ValueError(
            "Input JSON must be a list of resources or a document containing "
            "a top-level 'resources' list."
        )

    if not all(isinstance(resource, dict) for resource in resources):
        raise ValueError("Every resource in the input JSON must be a dictionary.")

    return resources


def create_snapshot_from_json_file(
    input_path: str | Path,
    *,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    key_field: str = "resource_id",
    ignore_fields: set[str] | None = None,
    collected_at: datetime | None = None,
) -> SnapshotRunResult:
    """Save a snapshot from a JSON file and optionally write a diff report."""

    resources = load_resources_from_json_file(input_path)

    snapshot_path = save_snapshot(
        resources,
        snapshot_dir=snapshot_dir,
        snapshot_name=snapshot_name,
        collected_at=collected_at,
        metadata={
            "source_file": str(Path(input_path)),
            "resource_count": len(resources),
        },
    )

    diff_report = create_latest_snapshot_diff_report(
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        snapshot_name=snapshot_name,
        key_field=key_field,
        ignore_fields=ignore_fields,
    )

    return SnapshotRunResult(
        snapshot_path=snapshot_path,
        diff_report=diff_report,
    )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Save a timestamped Guardian snapshot from JSON input and create "
            "a diff report when a previous snapshot exists."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSON file containing resources or a snapshot document.",
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

    parser.add_argument(
        "--key-field",
        default="resource_id",
        help="Field used to identify the same resource across snapshots.",
    )

    parser.add_argument(
        "--ignore-field",
        action="append",
        default=[],
        help=(
            "Field to ignore during diffing. Can be supplied multiple times, "
            "for example: --ignore-field collected_at --ignore-field scanned_at"
        ),
    )

    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv or sys.argv[1:])

    try:
        result = create_snapshot_from_json_file(
            args.input,
            snapshot_dir=args.snapshot_dir,
            report_dir=args.report_dir,
            snapshot_name=args.snapshot_name,
            key_field=args.key_field,
            ignore_fields=set(args.ignore_field),
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Snapshot saved: {result.snapshot_path}")

    if result.diff_report is None:
        print("Diff report skipped: fewer than two snapshots are available.")
    else:
        print(f"Diff report written: {result.diff_report.report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
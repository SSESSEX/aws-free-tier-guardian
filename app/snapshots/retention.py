"""Opt-in, count-based retention for generated snapshot history.

Only regular files with the selected snapshot name and a valid UTC timestamp
in the generated filename format are eligible. Cleanup is non-recursive and
does not read AWS credentials or connect to PostgreSQL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.snapshots.report import DEFAULT_DIFF_REPORT_DIR
from app.snapshots.store import (
    DEFAULT_SNAPSHOT_DIR,
    DEFAULT_SNAPSHOT_NAME,
    _normalise_snapshot_name,
)


@dataclass(frozen=True)
class SnapshotRetentionResult:
    """Generated files permanently removed by a completed cleanup."""

    deleted_snapshots: tuple[Path, ...]
    deleted_reports: tuple[Path, ...]


def validate_retention_count(retention_count: int) -> None:
    """Require an explicit integer limit that preserves two snapshots."""

    if type(retention_count) is not int or retention_count < 2:
        raise ValueError("retention_count must be an integer of at least 2.")


def _list_generated_files(
    directory: Path,
    *,
    snapshot_name: str,
    suffix: str,
) -> list[Path]:
    """List eligible regular files in chronological filename order."""

    if directory.is_symlink():
        raise ValueError(f"Retention directory must not be a symlink: {directory}")

    if not directory.exists():
        return []

    pattern = re.compile(
        rf"{re.escape(snapshot_name)}-([0-9]{{8}}T[0-9]{{6}}Z){re.escape(suffix)}"
    )
    paths = []

    for path in directory.iterdir():
        match = pattern.fullmatch(path.name)

        if match is None or path.is_symlink() or not path.is_file():
            continue

        try:
            datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ")
        except ValueError:
            continue

        paths.append(path)

    return sorted(paths)


def prune_snapshot_history(
    *,
    retention_count: int,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
) -> SnapshotRetentionResult:
    """Keep at most N snapshots and N Markdown diffs for one snapshot name.

    Each directory is capped independently using the timestamp in the filename,
    never the filesystem modification time. Missing directories are a no-op.
    Unrelated files, invalid timestamps, subdirectories, and file symlinks are
    left untouched. Directory symlinks are rejected.

    Both file lists are prepared before deleting anything. Deletion is permanent
    and filesystem errors propagate; already-completed deletions are not rolled
    back. Call this only after successfully generating the new batch artifacts.
    """

    validate_retention_count(retention_count)
    normalised_name = _normalise_snapshot_name(snapshot_name)

    snapshots = _list_generated_files(
        Path(snapshot_dir), snapshot_name=normalised_name, suffix=".json"
    )
    reports = _list_generated_files(
        Path(report_dir), snapshot_name=normalised_name, suffix="-diff.md"
    )

    deleted_snapshots = tuple(snapshots[:-retention_count])
    deleted_reports = tuple(reports[:-retention_count])

    for path in (*deleted_snapshots, *deleted_reports):
        path.unlink()

    return SnapshotRetentionResult(
        deleted_snapshots=deleted_snapshots,
        deleted_reports=deleted_reports,
    )

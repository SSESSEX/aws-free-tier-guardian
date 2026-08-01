"""Snapshot diff reporting utilities.

This module connects snapshot storage with deterministic diffing.

It loads the latest two snapshots, compares their resources, and writes a
human-readable Markdown report explaining what changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.snapshots.diff import ResourceChange, diff_resources
from app.snapshots.store import (
    DEFAULT_SNAPSHOT_DIR,
    DEFAULT_SNAPSHOT_NAME,
    get_latest_snapshot_path,
    get_previous_snapshot_path,
    load_snapshot,
)


DEFAULT_DIFF_REPORT_DIR = Path("reports/snapshot-diffs")


@dataclass(frozen=True)
class SnapshotDiffReport:
    """Represents a written snapshot diff report."""

    previous_snapshot_path: Path
    current_snapshot_path: Path
    report_path: Path
    summary: dict[str, int]


def _get_snapshot_resources(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    resources = snapshot.get("resources")

    if not isinstance(resources, list):
        raise ValueError("Snapshot document must contain a 'resources' list.")

    if not all(isinstance(resource, dict) for resource in resources):
        raise ValueError("Every snapshot resource must be a dictionary.")

    return resources


def _get_snapshot_label(snapshot: dict[str, Any]) -> str:
    snapshot_id = snapshot.get("snapshot_id")

    if isinstance(snapshot_id, str) and snapshot_id.strip():
        return snapshot_id

    return "unknown-snapshot"


def _get_resource_identifier(resource: dict[str, Any], key_field: str) -> str:
    resource_id = resource.get(key_field)

    if isinstance(resource_id, str) and resource_id.strip():
        return resource_id

    return "<missing-resource-id>"


def _format_resource_list(
    resources: list[dict[str, Any]],
    *,
    key_field: str,
) -> str:
    if not resources:
        return "_None._"

    lines = [
        f"- `{_get_resource_identifier(resource, key_field)}`"
        for resource in resources
    ]

    return "\n".join(lines)


def _format_changed_resources(changes: list[ResourceChange]) -> str:
    if not changes:
        return "_None._"

    lines = []

    for change in changes:
        changed_fields = ", ".join(
            f"`{field}`"
            for field in change.changed_fields
        )

        lines.append(
            f"- `{change.resource_id}` changed fields: {changed_fields}"
        )

    return "\n".join(lines)


def render_snapshot_diff_markdown(
    previous_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    diff_result: dict[str, Any],
    *,
    key_field: str = "resource_id",
) -> str:
    """Render a snapshot diff result as Markdown."""

    summary = diff_result["summary"]
    previous_label = _get_snapshot_label(previous_snapshot)
    current_label = _get_snapshot_label(current_snapshot)

    previous_collected_at = previous_snapshot.get("collected_at", "unknown")
    current_collected_at = current_snapshot.get("collected_at", "unknown")

    added = diff_result["added"]
    removed = diff_result["removed"]
    changed = diff_result["changed"]

    return f"""# Snapshot Diff Report

## Purpose

This report compares two AWS Free-Tier Guardian snapshots and records what changed between them.

The report is generated from saved snapshot files. It does not call AWS directly.

---

## Compared Snapshots

| Snapshot | Snapshot ID | Collected at |
|---|---|---|
| Previous | `{previous_label}` | `{previous_collected_at}` |
| Current | `{current_label}` | `{current_collected_at}` |

---

## Summary

| Change type | Count |
|---|---:|
| Previous resources | {summary["previous_count"]} |
| Current resources | {summary["current_count"]} |
| Added resources | {summary["added_count"]} |
| Removed resources | {summary["removed_count"]} |
| Changed resources | {summary["changed_count"]} |
| Unchanged resources | {summary["unchanged_count"]} |

---

## Added Resources

{_format_resource_list(added, key_field=key_field)}

---

## Removed Resources

{_format_resource_list(removed, key_field=key_field)}

---

## Changed Resources

{_format_changed_resources(changed)}

---

## Interpretation

Added resources are present in the current snapshot but were not present in the previous snapshot.

Removed resources were present in the previous snapshot but are no longer present in the current snapshot.

Changed resources exist in both snapshots, but one or more tracked fields changed.

Unchanged resources exist in both snapshots with no tracked field differences.

---

## Next Review Action

Review added, removed, and changed resources first. These are the resources most likely to represent account drift, configuration changes, or new governance risk.
"""


def write_snapshot_diff_report(
    previous_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    diff_result: dict[str, Any],
    *,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    key_field: str = "resource_id",
) -> Path:
    """Write a Markdown snapshot diff report to disk."""

    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    current_label = _get_snapshot_label(current_snapshot)
    output_path = output_dir / f"{current_label}-diff.md"

    markdown = render_snapshot_diff_markdown(
        previous_snapshot,
        current_snapshot,
        diff_result,
        key_field=key_field,
    )

    output_path.write_text(markdown, encoding="utf-8")

    return output_path


def create_latest_snapshot_diff_report(
    *,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    key_field: str = "resource_id",
    ignore_fields: set[str] | None = None,
) -> SnapshotDiffReport | None:
    """Create a diff report from the latest two saved snapshots.

    Returns None when fewer than two snapshots exist.
    """

    previous_snapshot_path = get_previous_snapshot_path(
        snapshot_dir,
        snapshot_name=snapshot_name,
    )

    current_snapshot_path = get_latest_snapshot_path(
        snapshot_dir,
        snapshot_name=snapshot_name,
    )

    if previous_snapshot_path is None or current_snapshot_path is None:
        return None

    previous_snapshot = load_snapshot(previous_snapshot_path)
    current_snapshot = load_snapshot(current_snapshot_path)

    previous_resources = _get_snapshot_resources(previous_snapshot)
    current_resources = _get_snapshot_resources(current_snapshot)

    diff_result = diff_resources(
        previous_resources,
        current_resources,
        key_field=key_field,
        ignore_fields=ignore_fields,
    )

    report_path = write_snapshot_diff_report(
        previous_snapshot,
        current_snapshot,
        diff_result,
        report_dir=report_dir,
        key_field=key_field,
    )

    return SnapshotDiffReport(
        previous_snapshot_path=previous_snapshot_path,
        current_snapshot_path=current_snapshot_path,
        report_path=report_path,
        summary=diff_result["summary"],
    )
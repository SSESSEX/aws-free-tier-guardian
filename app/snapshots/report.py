"""Snapshot diff reporting utilities.

This module connects snapshot storage with deterministic diffing.

It loads the latest two snapshots, compares their resources, and writes both a
human-readable Markdown report and a machine-readable JSON change document.
"""

from __future__ import annotations

import json
import re
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
SNAPSHOT_DIFF_SCHEMA_VERSION = "1.0"
SAFE_SNAPSHOT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass(frozen=True)
class SnapshotDiffReport:
    """Represents written Markdown and JSON snapshot diff reports."""

    previous_snapshot_path: Path
    current_snapshot_path: Path
    report_path: Path
    json_report_path: Path
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
        if SAFE_SNAPSHOT_ID_PATTERN.fullmatch(snapshot_id) is None:
            raise ValueError(
                "Snapshot 'snapshot_id' may contain only letters, numbers, "
                "periods, underscores, and hyphens."
            )
        return snapshot_id

    return "unknown-snapshot"


def _get_resource_identifier(resource: dict[str, Any], key_field: str) -> str:
    resource_id = resource.get(key_field)

    if isinstance(resource_id, str) and resource_id.strip():
        return resource_id

    return "<missing-resource-id>"


def _require_resource_identifier(resource: dict[str, Any], key_field: str) -> str:
    resource_id = resource.get(key_field)

    if not isinstance(resource_id, str) or not resource_id.strip():
        raise ValueError(
            f"Every diff resource must contain a non-empty string '{key_field}'."
        )

    return resource_id


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


def build_snapshot_diff_json_document(
    previous_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    diff_result: dict[str, Any],
    *,
    key_field: str = "resource_id",
) -> dict[str, Any]:
    """Build a versioned, JSON-serialisable resource-change document."""

    changes: list[dict[str, Any]] = []

    for resource in diff_result["added"]:
        changes.append(
            {
                "change_type": "added",
                "resource_id": _require_resource_identifier(resource, key_field),
                "changed_fields": [],
                "before": None,
                "after": resource,
            }
        )

    for resource in diff_result["removed"]:
        changes.append(
            {
                "change_type": "removed",
                "resource_id": _require_resource_identifier(resource, key_field),
                "changed_fields": [],
                "before": resource,
                "after": None,
            }
        )

    for change in diff_result["changed"]:
        if not isinstance(change, ResourceChange):
            raise ValueError("Changed diff entries must be ResourceChange objects.")

        changes.append(
            {
                "change_type": "changed",
                "resource_id": change.resource_id,
                "changed_fields": list(change.changed_fields),
                "before": change.before,
                "after": change.after,
            }
        )

    changes.sort(key=lambda change: (change["resource_id"], change["change_type"]))

    return {
        "schema_version": SNAPSHOT_DIFF_SCHEMA_VERSION,
        "key_field": key_field,
        "previous_snapshot": {
            "snapshot_id": _get_snapshot_label(previous_snapshot),
            "collected_at": previous_snapshot.get("collected_at", "unknown"),
        },
        "current_snapshot": {
            "snapshot_id": _get_snapshot_label(current_snapshot),
            "collected_at": current_snapshot.get("collected_at", "unknown"),
        },
        "summary": dict(diff_result["summary"]),
        "changes": changes,
    }


def write_snapshot_diff_json_report(
    previous_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
    diff_result: dict[str, Any],
    *,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    key_field: str = "resource_id",
) -> Path:
    """Atomically write a structured JSON snapshot diff to disk."""

    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    current_label = _get_snapshot_label(current_snapshot)
    output_path = output_dir / f"{current_label}-diff.json"
    temp_path = output_dir / f"{current_label}-diff.json.tmp"
    document = build_snapshot_diff_json_document(
        previous_snapshot,
        current_snapshot,
        diff_result,
        key_field=key_field,
    )

    temp_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(output_path)

    return output_path


def create_latest_snapshot_diff_report(
    *,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    key_field: str = "resource_id",
    ignore_fields: set[str] | None = None,
) -> SnapshotDiffReport | None:
    """Create Markdown and JSON diff reports from the latest two snapshots.

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
    json_report_path = write_snapshot_diff_json_report(
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
        json_report_path=json_report_path,
        summary=diff_result["summary"],
    )

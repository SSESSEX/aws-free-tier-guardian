"""Snapshot storage utilities.

This module saves and loads timestamped snapshot files.

It is intentionally independent from boto3/AWS collection code so that snapshot
storage can be tested deterministically without live cloud access.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SnapshotDocument = dict[str, Any]
SnapshotResource = dict[str, Any]


DEFAULT_SNAPSHOT_DIR = Path("reports/snapshots")
DEFAULT_SNAPSHOT_NAME = "aws-config"
SNAPSHOT_SCHEMA_VERSION = "1.0"


def _as_utc_datetime(value: datetime | None) -> datetime:
    """Return a timezone-aware UTC datetime."""

    if value is None:
        return datetime.now(timezone.utc)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _format_datetime_for_filename(value: datetime) -> str:
    """Format a datetime as a lexicographically sortable filename timestamp."""

    utc_value = _as_utc_datetime(value)
    return utc_value.strftime("%Y%m%dT%H%M%SZ")


def _format_datetime_for_json(value: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC timestamp."""

    utc_value = _as_utc_datetime(value)
    return utc_value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalise_snapshot_name(snapshot_name: str) -> str:
    """Convert a snapshot name into a safe lowercase filename prefix."""

    if not isinstance(snapshot_name, str) or not snapshot_name.strip():
        raise ValueError("snapshot_name must be a non-empty string.")

    cleaned = snapshot_name.strip().lower().replace("_", "-")
    cleaned = re.sub(r"[^a-z0-9-]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")

    if not cleaned:
        raise ValueError("snapshot_name must contain at least one alphanumeric character.")

    return cleaned


def build_snapshot_document(
    resources: list[SnapshotResource],
    *,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    collected_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> SnapshotDocument:
    """Build the JSON-serialisable snapshot document."""

    if not isinstance(resources, list):
        raise ValueError("resources must be a list of dictionaries.")

    if not all(isinstance(resource, dict) for resource in resources):
        raise ValueError("Every resource must be a dictionary.")

    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a dictionary when provided.")

    collected_at_utc = _as_utc_datetime(collected_at)
    normalised_name = _normalise_snapshot_name(snapshot_name)
    timestamp_for_filename = _format_datetime_for_filename(collected_at_utc)

    snapshot_id = f"{normalised_name}-{timestamp_for_filename}"

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "snapshot_name": normalised_name,
        "collected_at": _format_datetime_for_json(collected_at_utc),
        "resource_count": len(resources),
        "metadata": metadata or {},
        "resources": resources,
    }


def save_snapshot(
    resources: list[SnapshotResource],
    *,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    collected_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Save resources as a timestamped JSON snapshot.

    The write is performed through a temporary file and then atomically moved
    into place. This avoids leaving half-written JSON if the process fails
    during the write.

    Returns:
        Path to the saved snapshot file.
    """

    snapshot_document = build_snapshot_document(
        resources,
        snapshot_name=snapshot_name,
        collected_at=collected_at,
        metadata=metadata,
    )

    output_dir = Path(snapshot_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_id = snapshot_document["snapshot_id"]
    output_path = output_dir / f"{snapshot_id}.json"
    temp_path = output_dir / f"{snapshot_id}.json.tmp"

    temp_path.write_text(
        json.dumps(snapshot_document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    temp_path.replace(output_path)

    return output_path


def load_snapshot(snapshot_path: str | Path) -> SnapshotDocument:
    """Load a snapshot JSON file from disk."""

    path = Path(snapshot_path)

    if not path.exists():
        raise FileNotFoundError(f"Snapshot file does not exist: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def list_snapshot_paths(
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    *,
    snapshot_name: str | None = DEFAULT_SNAPSHOT_NAME,
) -> list[Path]:
    """List snapshot files in chronological filename order."""

    directory = Path(snapshot_dir)

    if not directory.exists():
        return []

    if snapshot_name is None:
        pattern = "*.json"
    else:
        normalised_name = _normalise_snapshot_name(snapshot_name)
        pattern = f"{normalised_name}-*.json"

    return sorted(
        path
        for path in directory.glob(pattern)
        if path.is_file()
    )


def get_latest_snapshot_path(
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    *,
    snapshot_name: str | None = DEFAULT_SNAPSHOT_NAME,
) -> Path | None:
    """Return the latest snapshot path, or None if no snapshots exist."""

    paths = list_snapshot_paths(snapshot_dir, snapshot_name=snapshot_name)

    if not paths:
        return None

    return paths[-1]


def get_previous_snapshot_path(
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    *,
    snapshot_name: str | None = DEFAULT_SNAPSHOT_NAME,
) -> Path | None:
    """Return the snapshot before the latest one, or None if unavailable."""

    paths = list_snapshot_paths(snapshot_dir, snapshot_name=snapshot_name)

    if len(paths) < 2:
        return None

    return paths[-2]
"""Deterministic snapshot diffing utilities.

This module compares two normalised resource snapshots and reports which
resources were added, removed, changed, or left unchanged.

It is intentionally AWS-agnostic so it can be tested without live AWS access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SnapshotResource = dict[str, Any]


@dataclass(frozen=True)
class ResourceChange:
    """Represents a resource that exists in both snapshots but changed."""

    resource_id: str
    changed_fields: list[str]
    before: SnapshotResource
    after: SnapshotResource


def _normalise_ignore_fields(ignore_fields: set[str] | None) -> set[str]:
    return ignore_fields or set()


def _without_ignored_fields(
    resource: SnapshotResource,
    ignore_fields: set[str],
) -> SnapshotResource:
    return {
        key: value
        for key, value in resource.items()
        if key not in ignore_fields
    }


def _index_resources(
    resources: list[SnapshotResource],
    key_field: str,
) -> dict[str, SnapshotResource]:
    indexed: dict[str, SnapshotResource] = {}

    for resource in resources:
        resource_id = resource.get(key_field)

        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError(
                f"Every resource must contain a non-empty string '{key_field}'."
            )

        if resource_id in indexed:
            raise ValueError(f"Duplicate resource id found: {resource_id}")

        indexed[resource_id] = resource

    return indexed


def _changed_fields(
    previous: SnapshotResource,
    current: SnapshotResource,
    ignore_fields: set[str],
) -> list[str]:
    previous_clean = _without_ignored_fields(previous, ignore_fields)
    current_clean = _without_ignored_fields(current, ignore_fields)

    all_fields = sorted(set(previous_clean) | set(current_clean))

    return [
        field
        for field in all_fields
        if previous_clean.get(field) != current_clean.get(field)
    ]


def diff_resources(
    previous_resources: list[SnapshotResource],
    current_resources: list[SnapshotResource],
    *,
    key_field: str = "resource_id",
    ignore_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Compare two resource snapshots.

    Args:
        previous_resources: Resources from the older snapshot.
        current_resources: Resources from the newer snapshot.
        key_field: Field used to identify the same resource across snapshots.
        ignore_fields: Fields to exclude from change detection, such as
            collection timestamps.

    Returns:
        A dictionary containing added, removed, changed, unchanged, and summary.
    """

    ignored = _normalise_ignore_fields(ignore_fields)

    previous_index = _index_resources(previous_resources, key_field)
    current_index = _index_resources(current_resources, key_field)

    previous_ids = set(previous_index)
    current_ids = set(current_index)

    added_ids = sorted(current_ids - previous_ids)
    removed_ids = sorted(previous_ids - current_ids)
    shared_ids = sorted(previous_ids & current_ids)

    added = [current_index[resource_id] for resource_id in added_ids]
    removed = [previous_index[resource_id] for resource_id in removed_ids]

    changed: list[ResourceChange] = []
    unchanged: list[SnapshotResource] = []

    for resource_id in shared_ids:
        previous_resource = previous_index[resource_id]
        current_resource = current_index[resource_id]

        fields = _changed_fields(previous_resource, current_resource, ignored)

        if fields:
            changed.append(
                ResourceChange(
                    resource_id=resource_id,
                    changed_fields=fields,
                    before=previous_resource,
                    after=current_resource,
                )
            )
        else:
            unchanged.append(current_resource)

    return {
        "summary": {
            "previous_count": len(previous_resources),
            "current_count": len(current_resources),
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "unchanged_count": len(unchanged),
        },
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }
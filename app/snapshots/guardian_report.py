"""Guardian report snapshot adapter.

This module converts the real AWS Free-Tier Guardian JSON report into a flat
list of snapshot resources.

The scanner report is nested by service. The snapshot system needs a flat list
where every tracked item has a stable resource_id, service, resource_type, and
configuration payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from app.snapshots.report import DEFAULT_DIFF_REPORT_DIR, SnapshotDiffReport
from app.snapshots.report import create_latest_snapshot_diff_report
from app.snapshots.store import DEFAULT_SNAPSHOT_DIR, DEFAULT_SNAPSHOT_NAME
from app.snapshots.store import SnapshotResource, save_snapshot


DEFAULT_GUARDIAN_REPORT_PATH = Path("reports/aws_guardian_report.json")


@dataclass(frozen=True)
class ResourceCollectionConfig:
    """Describes where resource lists live inside a service report."""

    collection_key: str
    resource_type: str
    id_fields: tuple[str, ...]


@dataclass(frozen=True)
class GuardianSnapshotResult:
    """Result from converting a Guardian report into a timestamped snapshot."""

    snapshot_path: Path
    diff_report: SnapshotDiffReport | None
    resource_count: int


SERVICE_RESOURCE_COLLECTIONS: dict[str, ResourceCollectionConfig] = {
    "s3": ResourceCollectionConfig(
        collection_key="buckets",
        resource_type="bucket",
        id_fields=("name",),
    ),
    "ec2": ResourceCollectionConfig(
        collection_key="instances",
        resource_type="instance",
        id_fields=("instance_id", "id"),
    ),
    "ebs": ResourceCollectionConfig(
        collection_key="volumes",
        resource_type="volume",
        id_fields=("volume_id", "id"),
    ),
    "eip": ResourceCollectionConfig(
        collection_key="elastic_ips",
        resource_type="elastic_ip",
        id_fields=("allocation_id", "public_ip", "public_ipv4_pool"),
    ),
    "security_groups": ResourceCollectionConfig(
        collection_key="security_groups",
        resource_type="security_group",
        id_fields=("group_id",),
    ),
    "cloudwatch_logs": ResourceCollectionConfig(
        collection_key="log_groups",
        resource_type="log_group",
        id_fields=("log_group_name", "logGroupName", "name", "arn"),
    ),
    "iam_access_keys": ResourceCollectionConfig(
        collection_key="access_keys",
        resource_type="access_key",
        id_fields=("user_name", "masked_access_key_id"),
    ),
    "cloudtrail": ResourceCollectionConfig(
        collection_key="trails",
        resource_type="trail",
        id_fields=("name", "Name", "trail_name", "trail_arn", "TrailARN"),
    ),
    "rds": ResourceCollectionConfig(
        collection_key="db_instances",
        resource_type="db_instance",
        id_fields=(
            "db_instance_identifier",
            "DBInstanceIdentifier",
            "db_instance_arn",
            "arn",
        ),
    ),
    "budgets": ResourceCollectionConfig(
        collection_key="budgets",
        resource_type="budget",
        id_fields=("budget_name", "BudgetName"),
    ),
}


def load_guardian_report(report_path: str | Path) -> dict[str, Any]:
    """Load a Guardian JSON report from disk."""

    path = Path(report_path)

    if not path.exists():
        raise FileNotFoundError(f"Guardian report does not exist: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Guardian report must be a JSON object.")

    return payload


def _stable_content_hash(resource: dict[str, Any]) -> str:
    """Build a stable hash for a resource when no configured ID field exists."""

    serialised = json.dumps(
        resource,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )

    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()[:12]


def _build_local_resource_id(
    resource: dict[str, Any],
    id_fields: tuple[str, ...],
) -> str:
    """Build a stable local resource ID from one or more configured fields."""

    values: list[str] = []

    for field in id_fields:
        value = resource.get(field)

        if value is not None and str(value).strip():
            values.append(str(value).strip())

    if values:
        return "/".join(values)

    return f"content-hash-{_stable_content_hash(resource)}"


def _build_snapshot_resource(
    *,
    service: str,
    resource_type: str,
    local_resource_id: str,
    configuration: dict[str, Any],
    aws_profile: str | None,
    aws_region: str | None,
) -> SnapshotResource:
    """Build the flattened resource shape used by snapshot diffing."""

    return {
        "resource_id": f"{service}:{resource_type}:{local_resource_id}",
        "service": service,
        "resource_type": resource_type,
        "source_resource_id": local_resource_id,
        "aws_profile": aws_profile,
        "aws_region": aws_region,
        "configuration": configuration,
    }


def extract_guardian_snapshot_resources(
    guardian_report: dict[str, Any],
) -> list[SnapshotResource]:
    """Flatten a Guardian scanner report into snapshot resources.

    Each service gets a service-summary resource so account-level posture can be
    tracked even when the service has no individual resources.

    Known service resource lists are also flattened into individual resources.
    """

    services = guardian_report.get("services")

    if not isinstance(services, dict):
        raise ValueError("Guardian report must contain a top-level 'services' object.")

    aws_profile = guardian_report.get("aws_profile")
    aws_region = guardian_report.get("aws_region")

    resources: list[SnapshotResource] = []

    for service_name in sorted(services):
        service_payload = services[service_name]

        if not isinstance(service_payload, dict):
            raise ValueError(f"Service payload must be an object: {service_name}")

        service_summary = service_payload.get("summary", {})

        if isinstance(service_summary, dict):
            resources.append(
                _build_snapshot_resource(
                    service=service_name,
                    resource_type="service_summary",
                    local_resource_id="summary",
                    configuration=service_summary,
                    aws_profile=aws_profile if isinstance(aws_profile, str) else None,
                    aws_region=aws_region if isinstance(aws_region, str) else None,
                )
            )

        collection_config = SERVICE_RESOURCE_COLLECTIONS.get(service_name)

        if collection_config is None:
            continue

        collection = service_payload.get(collection_config.collection_key, [])

        if not isinstance(collection, list):
            raise ValueError(
                f"Expected '{service_name}.{collection_config.collection_key}' "
                "to be a list."
            )

        for resource in collection:
            if not isinstance(resource, dict):
                raise ValueError(
                    f"Every item in '{service_name}."
                    f"{collection_config.collection_key}' must be an object."
                )

            local_resource_id = _build_local_resource_id(
                resource,
                collection_config.id_fields,
            )

            resources.append(
                _build_snapshot_resource(
                    service=service_name,
                    resource_type=collection_config.resource_type,
                    local_resource_id=local_resource_id,
                    configuration=resource,
                    aws_profile=aws_profile if isinstance(aws_profile, str) else None,
                    aws_region=aws_region if isinstance(aws_region, str) else None,
                )
            )

    return resources


def create_snapshot_from_guardian_report_file(
    report_path: str | Path = DEFAULT_GUARDIAN_REPORT_PATH,
    *,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    report_dir: str | Path = DEFAULT_DIFF_REPORT_DIR,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
    collected_at: datetime | None = None,
) -> GuardianSnapshotResult:
    """Convert a Guardian report into a snapshot and optional diff reports."""

    guardian_report = load_guardian_report(report_path)
    resources = extract_guardian_snapshot_resources(guardian_report)

    snapshot_path = save_snapshot(
        resources,
        snapshot_dir=snapshot_dir,
        snapshot_name=snapshot_name,
        collected_at=collected_at,
        metadata={
            "source_report": str(Path(report_path)),
            "resource_count": len(resources),
            "scanner_scan_time": guardian_report.get("scan_time"),
            "aws_profile": guardian_report.get("aws_profile"),
            "aws_region": guardian_report.get("aws_region"),
        },
    )

    diff_report = create_latest_snapshot_diff_report(
        snapshot_dir=snapshot_dir,
        report_dir=report_dir,
        snapshot_name=snapshot_name,
    )

    return GuardianSnapshotResult(
        snapshot_path=snapshot_path,
        diff_report=diff_report,
        resource_count=len(resources),
    )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a Guardian scanner JSON report into a timestamped snapshot "
            "and create diff reports when a previous snapshot exists."
        )
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_GUARDIAN_REPORT_PATH),
        help="Path to reports/aws_guardian_report.json.",
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
        help="Logical snapshot name used as the snapshot filename prefix.",
    )

    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv or sys.argv[1:])

    try:
        result = create_snapshot_from_guardian_report_file(
            args.input,
            snapshot_dir=args.snapshot_dir,
            report_dir=args.report_dir,
            snapshot_name=args.snapshot_name,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Snapshot saved: {result.snapshot_path}")
    print(f"Snapshot resources: {result.resource_count}")

    if result.diff_report is None:
        print("Diff report skipped: fewer than two snapshots are available.")
    else:
        print(f"Diff report written: {result.diff_report.report_path}")
        print(f"JSON diff report written: {result.diff_report.json_report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

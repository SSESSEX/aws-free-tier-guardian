# Snapshot Diff Report

## Purpose

This report compares two AWS Free-Tier Guardian snapshots and records what changed between them.

The report is generated from saved snapshot files. It does not call AWS directly.

---

## Compared Snapshots

| Snapshot | Snapshot ID | Collected at |
|---|---|---|
| Previous | `aws-config-20260115T090000Z` | `2026-01-15T09:00:00Z` |
| Current | `aws-config-20260115T100000Z` | `2026-01-15T10:00:00Z` |

---

## Summary

| Change type | Count |
|---|---:|
| Previous resources | 4 |
| Current resources | 4 |
| Added resources | 1 |
| Removed resources | 1 |
| Changed resources | 1 |
| Unchanged resources | 2 |

---

## Added Resources

- `security_groups:security_group:sg-example-new`

---

## Removed Resources

- `security_groups:security_group:sg-example-old`

---

## Changed Resources

- `s3:bucket:example-ingest-bucket` changed fields: `configuration`

---

## Interpretation

Added resources are present in the current snapshot but were not present in the previous snapshot.

Removed resources were present in the previous snapshot but are no longer present in the current snapshot.

Changed resources exist in both snapshots, but one or more tracked fields changed.

Unchanged resources exist in both snapshots with no tracked field differences.

---

## Next Review Action

Review added, removed, and changed resources first. These are the resources most likely to represent account drift, configuration changes, or new governance risk.

# Batch Snapshot Monitoring Runbook

## Purpose

This runbook explains how to run AWS Free-Tier Guardian as a batch governance
monitor.

The batch command performs one read-only AWS scan, saves the current account
state as a timestamped JSON snapshot, and compares it with the previous
snapshot when one is available. The result is a local history of account state
and a human-readable record of what changed between runs.

This is batch monitoring, not real-time or event-driven monitoring. Changes are
detected the next time the command runs.

## Architecture

```text
AWS account configuration
        ↓
read-only boto3 scanner
        ↓
reports/aws_guardian_report.json
        ↓
flatten service summaries and resources
        ↓
reports/snapshots/aws-config-<timestamp>.json
        ↓
compare the latest two snapshots
        ↓
reports/snapshot-diffs/aws-config-<timestamp>-diff.md
```

The scanner report adapter converts the nested service report into a flat list
of deterministic snapshot resources. The diff layer is AWS-agnostic: it
compares those flat resources by `resource_id` without making additional AWS
calls.

This workflow implements the batch-first decision recorded in
[ADR 001: Use Batch Automation Before Event-Driven Monitoring](../architecture/adr-001-batch-first-automation.md):

```text
collect → snapshot → compare → report → persist
```

Persistence currently means local JSON snapshots and Markdown diff reports.
PostgreSQL history and scheduled execution are optional later improvements.

## Prerequisites

Run the commands in this guide from the repository root.

Before running the batch monitor, confirm that:

- Python dependencies are installed in the local virtual environment.
- `.env` contains the local AWS profile and region configuration.
- The configured AWS CLI profile exists on the machine.
- The profile has the read-only permissions required by the scanners.
- `.env` and `reports/` remain untracked by Git.

Create and prepare the virtual environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For an existing environment, activate it:

```bash
source .venv/bin/activate
```

Do not place AWS credentials directly in source files, documentation, test
fixtures, or command examples. The scanner uses the locally configured AWS CLI
profile identified by `AWS_PROFILE`.

## Run the Batch Monitor

Run the full scan, snapshot, and diff loop:

```bash
python -m app.snapshots.run_guardian_batch
```

The repository also provides a Bash wrapper for repeatable local execution:

```bash
./scripts/run_guardian_batch.sh
```

The wrapper resolves the repository root, uses `.venv/bin/python` when it is
available, fails immediately if the batch runner fails, and prints the snapshot
and diff-report directories after a successful run. Any batch-runner arguments
are forwarded unchanged. For example:

```bash
./scripts/run_guardian_batch.sh --snapshot-name portfolio-scan
```

The command runs these steps in order:

1. Run `app.scanner.run_all` as a subprocess.
2. Confirm that `reports/aws_guardian_report.json` was produced.
3. Convert the nested Guardian report into flat snapshot resources.
4. Save a timestamped JSON snapshot.
5. Load the latest and previous snapshots when both exist.
6. Write a Markdown diff report.

The batch command does not enable PostgreSQL persistence and does not schedule
future runs.

## Expected Output

On the first successful run, expect output similar to:

```text
Guardian batch run completed successfully.
Scanner report: reports/aws_guardian_report.json
Snapshot saved: reports/snapshots/aws-config-<timestamp>.json
Snapshot resources: <resource-count>
Diff report skipped: fewer than two snapshots are available.
```

Skipping the diff on the first run is expected because there is no previous
snapshot to compare.

On a later successful run, expect:

```text
Guardian batch run completed successfully.
Scanner report: reports/aws_guardian_report.json
Snapshot saved: reports/snapshots/aws-config-<timestamp>.json
Snapshot resources: <resource-count>
Diff report written: reports/snapshot-diffs/aws-config-<timestamp>-diff.md
```

The resource count depends on the services and resources visible to the
configured AWS profile. It includes one `service_summary` resource per service
in the Guardian report as well as the individual AWS resources collected for
that service.

## Snapshot Output

Snapshots are written to:

```text
reports/snapshots/
```

The default filename format is:

```text
aws-config-YYYYMMDDTHHMMSSZ.json
```

Each snapshot document contains:

- a schema version;
- a timestamp-based snapshot ID;
- the UTC collection time;
- the resource count;
- scanner metadata;
- a flat `resources` list.

An individual resource is shaped approximately like:

```json
{
  "resource_id": "s3:bucket:example-bucket",
  "service": "s3",
  "resource_type": "bucket",
  "configuration": {}
}
```

The exact configuration fields depend on the source service. Snapshot files
may contain private resource names, configuration details, AWS profile names,
or other account-specific metadata. Treat them as local operational output.

## Diff Report Output

Diff reports are written to:

```text
reports/snapshot-diffs/
```

The default filename format is:

```text
aws-config-YYYYMMDDTHHMMSSZ-diff.md
```

Each report identifies the previous and current snapshots and summarizes:

```text
Previous resources
Current resources
Added resources
Removed resources
Changed resources
Unchanged resources
```

Changed resources also list the top-level fields that differ. The report does
not call AWS; it is generated entirely from the two saved snapshot files.

## How to Interpret the Report

| Category | Meaning | Suggested review |
|---|---|---|
| Added | Present in the current snapshot but absent from the previous snapshot | Confirm that the new resource or service state is expected. |
| Removed | Present in the previous snapshot but absent from the current snapshot | Confirm whether the resource was intentionally deleted or became invisible to the scanner. |
| Changed | The same `resource_id` exists in both snapshots, but tracked fields differ | Review the listed fields and decide whether the configuration drift is expected. |
| Unchanged | The same `resource_id` and tracked data exist in both snapshots | No immediate drift review is required. |

A changed or added resource is not automatically a security incident. The diff
reports observed state changes; the scanner findings explain whether the
current state violates a governance or cost-safety rule.

Review added, removed, and changed resources first. If a change is unexpected,
confirm it in AWS using the same read-only profile before taking any action.

## Why Reports Are Not Committed

The repository ignores `/reports/` because generated output can contain:

- AWS resource names and identifiers;
- account-specific configuration;
- AWS profile names or regions;
- findings that reveal private infrastructure details;
- timestamped local scan history.

Confirm the ignore rule when needed:

```bash
git check-ignore -v reports/
```

Before committing any change, check the working tree:

```bash
git status --short
```

Do not force-add files from `reports/`. If a test needs realistic report data,
create a deliberately sanitised fixture under `tests/fixtures/` with invented
account details and resource names.

## Troubleshooting

### The scanner exits with an error

Run the scanner by itself to expose the original error:

```bash
python -m app.scanner.run_all
```

Check that the virtual environment is active, dependencies are installed, and
the AWS profile named in `.env` exists locally. Do not paste credentials or
private account output into issues, commits, or public logs.

### The scanner succeeds but the JSON report is missing

The batch runner expects:

```text
reports/aws_guardian_report.json
```

Confirm whether the file exists:

```bash
test -f reports/aws_guardian_report.json && echo "report found"
```

If the scanner uses a deliberately different report path, pass the same path to
the batch runner:

```bash
python -m app.snapshots.run_guardian_batch \
  --scanner-report-path path/to/aws_guardian_report.json
```

### The diff report is skipped

The latest-two comparison requires at least two snapshot files with the same
snapshot name. Run the batch monitor again after the account state is collected
at a later time.

List the available default snapshots:

```bash
find reports/snapshots -maxdepth 1 -type f -name 'aws-config-*.json' -print
```

### Convert an existing Guardian report without running AWS again

If a valid local scanner report already exists, convert it directly:

```bash
python -m app.snapshots.guardian_report \
  --input reports/aws_guardian_report.json
```

This creates a new snapshot from the existing report and writes a diff report
when a previous snapshot is available. It does not perform a fresh AWS scan.

### The snapshot count is lower than expected

Check the `services` object in the local Guardian JSON report. The adapter can
only flatten services and resources present in that report. Missing resources
may indicate limited profile permissions, a scanner error, an unsupported
service shape, or an account that genuinely has no resources of that type.

Do not commit the report while investigating.

## Next Improvements

Keep subsequent changes small and testable. Suitable next steps are:

1. Add a Bash wrapper that resolves the repository root and uses `.venv` when
   available.
2. Add structured JSON diff output alongside the Markdown report.
3. Add optional PostgreSQL history after the file-based output is stable.
4. Add scheduled execution after the manual batch workflow is documented and
   reliable.

Event-driven monitoring remains a future extension. The current honest project
description is **batch governance monitoring tool**.

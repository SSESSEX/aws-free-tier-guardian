# Kubernetes Manifests

This directory contains local Kubernetes manifests for AWS Free-Tier Guardian.

The project uses `kind` for local Kubernetes development. The scanner image is built locally, loaded into the kind cluster, and executed through Kubernetes Jobs or CronJobs.

## Resources

This directory includes manifests for:

* Namespace
* PostgreSQL PersistentVolumeClaim
* Snapshot and report PersistentVolumeClaim
* PostgreSQL Deployment
* PostgreSQL Service
* Scanner Job
* Scanner CronJob

Secrets and ConfigMaps are created manually during local setup and are not committed with real values.

## Build and Load Scanner Image

From the project root:

```bash
docker build -t aws-free-tier-guardian-scanner:local .
kind load docker-image aws-free-tier-guardian-scanner:local --name aws-guardian
```

## Apply Kubernetes Resources

From the project root:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/reports-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/scanner-cronjob.yaml
```

The reports PVC preserves scanner reports, JSON snapshots, and Markdown diffs
between Job Pods. PostgreSQL uses its own separate PVC.

The CronJob keeps at most **672 snapshots and 672 Markdown diffs** for the
default snapshot name after each successful batch. Older matching files are
permanently deleted. This is roughly seven days at the 15-minute schedule, not
a disk-size guarantee. PostgreSQL history is not pruned. Read the
[retention policy](../docs/runbooks/batch-snapshot-monitoring.md#snapshot-retention)
before enabling it, and follow the [update procedure](../docs/kubernetes-runbook.md#deploy-a-retention-update)
to deploy the new image and manifest to an existing cluster.

## Trigger a Manual Batch Run

Suspend the CronJob and let running scanner Jobs finish before a manual run on
the shared PVC. `concurrencyPolicy: Forbid` does not protect independent Jobs.

```bash
kubectl -n aws-guardian create job manual-guardian-scan \
  --from=cronjob/aws-guardian-scan
```

The Job inherits PostgreSQL persistence and retention from the CronJob:

```text
python -m app.snapshots.run_guardian_batch --write-db --retention-count 672
```

The separate `scanner-job.yaml` omits retention by default. Its files still
share the PVC and remain eligible for cleanup by subsequent scheduled runs.

## View Scan Logs

```bash
kubectl -n aws-guardian logs job/manual-guardian-scan
```

## Delete Manual Scan Job

```bash
kubectl -n aws-guardian delete job manual-guardian-scan
```

## Check Resources

```bash
kubectl -n aws-guardian get all
kubectl -n aws-guardian get secrets
kubectl -n aws-guardian get configmaps
kubectl -n aws-guardian get pvc
```

## Detailed Runbook

For the full local Kubernetes setup and operational commands, see:

```text
docs/kubernetes-runbook.md
```

## Security Note

Do not commit real Kubernetes Secrets, AWS credentials, database passwords, `.env` files, or generated reports.

The committed manifests reference Kubernetes Secrets by name, but the real secret values are created locally and excluded from version control.

The reports PVC contains private AWS inventory. Keep the local kind cluster and
its Docker storage private, and remember that deleting the namespace or cluster
also deletes its retained report history.

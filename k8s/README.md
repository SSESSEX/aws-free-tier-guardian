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

## Trigger a Manual Batch Run

```bash
kubectl -n aws-guardian create job manual-guardian-scan \
  --from=cronjob/aws-guardian-scan
```

The Job runs the unified batch command with PostgreSQL persistence enabled:

```text
python -m app.snapshots.run_guardian_batch --write-db
```

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

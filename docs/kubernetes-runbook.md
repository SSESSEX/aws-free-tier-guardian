# Kubernetes Runbook

This runbook contains local Kubernetes commands for running AWS Free-Tier Guardian with kind.

## Cluster

Create the local kind cluster:

```bash
kind create cluster --name aws-guardian
```

Check the cluster:

```bash
kind get clusters
kubectl get nodes
kubectl cluster-info --context kind-aws-guardian
```

Delete the local cluster:

```bash
kind delete cluster --name aws-guardian
```

## Build and load scanner image

Build the scanner Docker image:

```bash
docker build -t aws-free-tier-guardian-scanner:local .
```

Load the image into the kind cluster:

```bash
kind load docker-image aws-free-tier-guardian-scanner:local --name aws-guardian
```

Important: after changing scanner code, rebuild and reload the image before rerunning Kubernetes Jobs or CronJobs.

## Namespace

Apply the namespace:

```bash
kubectl apply -f k8s/namespace.yaml
```

Check namespace resources:

```bash
kubectl -n aws-guardian get all
```

## Secrets and ConfigMaps

Create PostgreSQL secret:

```bash
kubectl create secret generic guardian-postgres-secret \
  -n aws-guardian \
  --from-literal=POSTGRES_DB=guardian \
  --from-literal=POSTGRES_USER=guardian_user \
  --from-literal=POSTGRES_PASSWORD=change_me \
  --dry-run=client -o yaml | kubectl apply -f -
```

Create AWS credentials secret from local AWS config:

```bash
kubectl create secret generic guardian-aws-credentials \
  -n aws-guardian \
  --from-file=credentials=$HOME/.aws/credentials \
  --from-file=config=$HOME/.aws/config \
  --dry-run=client -o yaml | kubectl apply -f -
```

Create app secret:

```bash
kubectl create secret generic guardian-app-secret \
  -n aws-guardian \
  --from-literal=DATABASE_URL=postgresql://<postgres-user>:<postgres-password>@guardian-postgres:5432/<postgres-db> \
  --dry-run=client -o yaml | kubectl apply -f -
```

Create schema ConfigMap:

```bash
kubectl create configmap guardian-postgres-schema \
  -n aws-guardian \
  --from-file=001_schema.sql=app/storage/schema.sql \
  --dry-run=client -o yaml | kubectl apply -f -
```

View secrets safely:

```bash
kubectl -n aws-guardian get secrets
kubectl -n aws-guardian describe secret guardian-postgres-secret
kubectl -n aws-guardian describe secret guardian-aws-credentials
kubectl -n aws-guardian describe secret guardian-app-secret
```

Avoid decoding or printing secret values unless absolutely necessary.

## PostgreSQL

Apply PostgreSQL resources:

```bash
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
```

Check rollout:

```bash
kubectl -n aws-guardian rollout status deployment/guardian-postgres
kubectl -n aws-guardian get pods
```

Verify tables:

```bash
kubectl -n aws-guardian exec deploy/guardian-postgres -- \
  psql -U guardian_user -d guardian -c "\dt"
```

Query scan runs:

```bash
kubectl -n aws-guardian exec deploy/guardian-postgres -- \
  psql -U guardian_user -d guardian -c "SELECT id, scan_time, aws_region FROM scan_runs ORDER BY id DESC;"
```

Query resource counts:

```bash
kubectl -n aws-guardian exec deploy/guardian-postgres -- \
  psql -U guardian_user -d guardian -c "SELECT service, resource_type, COUNT(*) FROM resources GROUP BY service, resource_type ORDER BY service;"
```

## Persistent batch reports

Apply the separate reports PVC:

```bash
kubectl apply -f k8s/reports-pvc.yaml
```

Confirm that both database and report storage are bound:

```bash
kubectl -n aws-guardian get pvc
```

The scanner workloads mount `guardian-reports-pvc` at `/app/reports`. This
preserves scanner reports, timestamped JSON snapshots, and Markdown diff
reports between completed Job Pods. The volume contains private AWS inventory
and must not be exported to the repository.

## Unified batch Job

Apply one-off scanner Job:

```bash
kubectl apply -f k8s/scanner-job.yaml
```

Check Job and Pod:

```bash
kubectl -n aws-guardian get jobs,pods
```

View logs:

```bash
kubectl -n aws-guardian logs job/aws-guardian-scan
```

The Job runs:

```text
python -m app.snapshots.run_guardian_batch --write-db
```

The first run writes a snapshot and skips its diff. Later runs compare against
the previous snapshot retained on `guardian-reports-pvc`.

Delete and rerun one-off Job:

```bash
kubectl -n aws-guardian delete job aws-guardian-scan
kubectl apply -f k8s/scanner-job.yaml
```

## Unified batch CronJob

Apply CronJob:

```bash
kubectl apply -f k8s/scanner-cronjob.yaml
```

The CronJob uses the same unified batch command as the one-off Job. Its
`Forbid` concurrency policy prevents overlapping runs from writing snapshots
to the reports PVC simultaneously.

Check CronJob:

```bash
kubectl -n aws-guardian get cronjobs
```

Create manual Job from CronJob:

```bash
kubectl -n aws-guardian create job manual-guardian-scan \
  --from=cronjob/aws-guardian-scan
```

View manual Job logs:

```bash
kubectl -n aws-guardian logs job/manual-guardian-scan
```

Delete manual Job:

```bash
kubectl -n aws-guardian delete job manual-guardian-scan
```

Suspend scheduled scans:

```bash
kubectl -n aws-guardian patch cronjob aws-guardian-scan \
  -p '{"spec":{"suspend":true}}'
```

Resume scheduled scans:

```bash
kubectl -n aws-guardian patch cronjob aws-guardian-scan \
  -p '{"spec":{"suspend":false}}'
```

## Cleanup

Warning: deleting the namespace or kind cluster also deletes the PostgreSQL and
report PVC data, including retained snapshot history.

Delete Kubernetes app resources:

```bash
kubectl delete namespace aws-guardian
```

Delete the entire kind cluster:

```bash
kind delete cluster --name aws-guardian
```

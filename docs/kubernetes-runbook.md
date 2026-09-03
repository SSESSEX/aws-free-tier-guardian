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

Check both database and report storage:

```bash
kubectl -n aws-guardian get pvc
```

If the reports claim is `Pending` and its StorageClass uses
`WaitForFirstConsumer`, create the first scanner Job before expecting `Bound`.
Provisioning waits for a Pod that uses the claim. This is expected behavior,
not a reason to delete the PVC. See [volume binding mode](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode).

The scanner workloads mount `guardian-reports-pvc` at `/app/reports`. This
preserves scanner reports, timestamped JSON snapshots, and Markdown/JSON diff
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

The CronJob adds explicit file retention to the unified command:

```text
python -m app.snapshots.run_guardian_batch --write-db --retention-count 672
```

After a successful batch it permanently deletes older matching files to retain
at most 672 timestamped snapshots, 672 Markdown diffs, and 672 structured JSON
diffs. At the configured 15-minute cadence this is approximately seven days,
not an exact age window or byte limit. PostgreSQL records and current scanner
reports are untouched.
Back up required history privately before enabling this policy. For details,
see [Snapshot Retention](runbooks/batch-snapshot-monitoring.md#snapshot-retention).

The `Forbid` policy prevents overlap among this CronJob's scheduled Jobs. It
does not serialize independently created manual Jobs: suspend scheduling and
wait for active scanner Jobs to finish before any manual run on the shared PVC.

Check CronJob:

```bash
kubectl -n aws-guardian get cronjobs
```

Create a manual Job from the CronJob (including its retention setting):

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

## Deploy a retention update

This updates an existing local kind deployment. It does not rotate credentials,
alter PostgreSQL data, or recreate PVCs. The first retention-enabled run can
remove old report history above the configured count; back up anything needed.

Suspend future runs and inspect existing Jobs:

```bash
kubectl -n aws-guardian patch cronjob aws-guardian-scan \
  -p '{"spec":{"suspend":true}}'
kubectl -n aws-guardian get jobs
```

Wait for any active scanner Jobs to finish before continuing. Suspension does
not stop Jobs that are already running.

Rebuild and load the image **before** applying the new flag:

```bash
docker build -t aws-free-tier-guardian-scanner:local .
kind load docker-image aws-free-tier-guardian-scanner:local --name aws-guardian
kubectl apply -f k8s/scanner-cronjob.yaml
```

Keep scheduling suspended during one manual verification:

```bash
kubectl -n aws-guardian patch cronjob aws-guardian-scan \
  -p '{"spec":{"suspend":true}}'
kubectl -n aws-guardian create job guardian-retention-check \
  --from=cronjob/aws-guardian-scan
kubectl -n aws-guardian wait --for=condition=complete \
  job/guardian-retention-check --timeout=180s
kubectl -n aws-guardian logs job/guardian-retention-check
```

Expect a successful batch and a `Retention:` line. Counts of zero are correct
when fewer than 673 eligible files exist. Do not lower the count on real history
just to test deletion; the unit tests exercise pruning using temporary files.
If the Job fails, inspect its logs and leave scheduling suspended until resolved.

After verification, remove only the temporary Job and resume scheduling:

```bash
kubectl -n aws-guardian delete job guardian-retention-check
kubectl -n aws-guardian patch cronjob aws-guardian-scan \
  -p '{"spec":{"suspend":false}}'
```

Deleting the temporary Job does not delete retained PVC files. To disable
automatic file cleanup, remove both `--retention-count` and its value from the
CronJob manifest, then reapply it. Already-pruned files are not restored.

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

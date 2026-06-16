# AWS Free-Tier Guardian

![Python Tests](https://github.com/SSESSEX/aws-free-tier-guardian/actions/workflows/tests.yml/badge.svg)

AWS Free-Tier Guardian is a Python-based AWS governance scanner that inspects cost, security, tagging, and configuration risks across multiple AWS services.

The project is designed as a practical cloud/data engineering portfolio project, combining AWS APIs, Python, PostgreSQL, Docker, Kubernetes, CI/CD, and automated rule testing.

---

## Current Status

AWS Free-Tier Guardian currently scans:

* S3 buckets
* EC2 instances
* EBS volumes
* Elastic IPs
* Security groups
* CloudWatch Log Groups
* IAM access keys
* CloudTrail trails
* RDS DB instances

The scanner produces:

* JSON scan reports
* Markdown executive reports
* PostgreSQL persistence
* Global risk summaries
* Service-level findings
* Unit-tested rule evaluation
* Dockerized execution
* Kubernetes Job and CronJob orchestration

Current test coverage:

```text
140 passing tests
```

---

## Architecture Snapshot

```text
AWS APIs
  ↓
Python boto3 scanners
  ↓
Rule evaluation engine
  ↓
Global summary builder
  ↓
JSON report + Markdown executive report
  ↓
PostgreSQL persistence
  ↓
Docker Compose / Kubernetes CronJob execution
```

For a more detailed architecture view, see [`docs/architecture.md`](docs/architecture.md).
---

## Core Features

### AWS service scanning

The scanner collects resource metadata from AWS using read-only IAM permissions. Each scanner normalizes service-specific AWS responses into structured Python dictionaries.

### Rule evaluation

Each service has a dedicated rules module that evaluates resources for cost, security, tagging, and configuration risks.

Example checks include:

* S3 bucket versioning and encryption
* EC2 running instance detection
* EBS unattached volume detection
* Elastic IP association checks
* Security group public inbound exposure
* CloudWatch Log Group retention checks
* IAM access key age and last-used checks
* CloudTrail logging visibility
* RDS public accessibility, encryption, backup retention, and deletion protection

### Global summary reporting

The combined scanner report includes an executive-level summary:

* Overall account status
* Number of services scanned
* Number of resources scanned
* Total findings
* Warning and failure counts
* Resources by service
* Service-level statuses
* Top risks across all scanned services

### PostgreSQL persistence

Scan results can be persisted to PostgreSQL using a normalized schema:

* `scan_runs`
* `resources`
* `findings`

Raw resource metadata is stored as JSONB while findings remain queryable for analytics.

### Reporting

The scanner writes both:

```text
reports/aws_guardian_report.json
reports/aws_guardian_report.md
```

The JSON report is machine-readable. The Markdown report is designed for human-readable review.

---

## Local Usage

Run all scanners and write local reports:

```bash
python3 -m app.scanner.run_all
```

Run all scanners and persist results to PostgreSQL:

```bash
python3 -m app.scanner.run_all --write-db
```

Run tests locally:

```bash
python3 -m pytest
```

Run tests inside Docker:

```bash
docker compose build scanner
docker compose run --rm scanner python -m pytest
```

---

## Docker Usage

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Run the scanner through Docker Compose:

```bash
docker compose run --rm scanner python -m app.scanner.run_all --write-db
```

Run tests through Docker Compose:

```bash
docker compose run --rm scanner python -m pytest
```

---

## Kubernetes

Local Kubernetes manifests are stored in:

```text
k8s/
```

This project uses `kind` for local Kubernetes development. The scanner image is built locally and loaded into the kind cluster.

Kubernetes resources include:

* Namespace
* PostgreSQL PersistentVolumeClaim
* PostgreSQL Deployment
* PostgreSQL Service
* Scanner Job
* Scanner CronJob
* ConfigMap for database schema
* Secrets for PostgreSQL, AWS credentials, and application configuration

Build and load the scanner image into kind:

```bash
docker build -t aws-free-tier-guardian-scanner:local .
kind load docker-image aws-free-tier-guardian-scanner:local --name aws-guardian
```

Apply Kubernetes resources:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/scanner-cronjob.yaml
```

Trigger a manual scan from the CronJob:

```bash
kubectl -n aws-guardian create job manual-guardian-scan \
  --from=cronjob/aws-guardian-scan
```

View scan logs:

```bash
kubectl -n aws-guardian logs job/manual-guardian-scan
```

Delete the manual job:

```bash
kubectl -n aws-guardian delete job manual-guardian-scan
```

---

## Testing

The project includes unit tests for scanner rule logic and reporting utilities.

Current test areas include:

* S3 rules
* EC2 rules
* EBS rules
* Elastic IP rules
* Security group rules
* CloudWatch Logs rules
* IAM access key rules
* CloudTrail rules
* RDS rules
* Global scan summary generation
* Markdown report generation

Run all tests:

```bash
python3 -m pytest
```

---

## Security Model

AWS Free-Tier Guardian is designed around least privilege.

The scanner uses read-only IAM permissions for each supported AWS service. It does not create, modify, start, stop, rotate, or delete AWS resources.

Sensitive files are excluded from version control, including:

```text
.env
reports/
.venv/
```

AWS credentials are provided locally through the AWS CLI profile and, in Kubernetes, through a Kubernetes Secret mounted into the scanner container.

---

## Example Output

Example console summary:

```text
Overall status: WARN
Services scanned: 9
Resources scanned: 4
Total findings: 20
Warnings: 4
Failures: 0

Top risks:
- [HIGH] cloudtrail / account / CLOUDTRAIL_TRAIL_EXISTS
- [MEDIUM] s3 / bucket / S3_VERSIONING
- [LOW] security_groups / security_group / SG_REQUIRED_TAGS
```

---

## Project Purpose

This project demonstrates practical cloud engineering and data engineering skills, including:

* AWS API integration with boto3
* IAM least-privilege design
* Rule-based governance scanning
* Python package structure
* PostgreSQL persistence
* JSONB storage
* SQL analytics readiness
* Dockerized execution
* Kubernetes Job and CronJob orchestration
* GitHub Actions CI
* Automated testing
* Human-readable reporting

---

## Roadmap

Potential future improvements:

* Terraform/OpenTofu infrastructure definitions
* Additional AWS service scanners
* Historical trend dashboard
* FastAPI reporting endpoint
* Streamlit or React dashboard
* More advanced cost-risk scoring
* Alerting for high-risk findings

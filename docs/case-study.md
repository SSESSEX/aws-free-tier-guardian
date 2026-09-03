# AWS Free-Tier Guardian Case Study

## Overview

AWS Free-Tier Guardian is a Python-based AWS governance scanner designed to detect cost, security, tagging, and configuration risks across an AWS account.

The project was built as a cloud and data engineering portfolio project, combining AWS APIs, Infrastructure as Code, containerisation, orchestration, relational persistence, automated reporting, CI/CD, and security-focused documentation.

## Problem

Cloud environments can become risky or expensive when resources are created without consistent governance.

Common issues include:

* Unattached EBS volumes
* Unassociated Elastic IPs
* Publicly exposed security groups
* Missing CloudTrail audit logging
* Missing CloudWatch log retention
* Disabled S3 versioning
* Public S3 policy risks
* Weak IAM access key hygiene
* Missing resource tags
* RDS configuration risks

For small teams, students, and early-stage cloud projects, these issues can easily be missed.

## Solution

AWS Free-Tier Guardian scans supported AWS services using read-only API calls, evaluates each resource against rule-based checks, and produces structured reports.

The scanner outputs:

* JSON reports for machine-readable analysis
* Markdown executive reports for human review
* PostgreSQL records for historical scan storage
* Timestamped snapshots with Markdown and structured JSON change reports
* Risk summaries grouped by service, severity, and resource type

## Services Covered

The current scanner covers:

* S3
* EC2
* EBS
* Elastic IPs
* Security Groups
* CloudWatch Logs
* IAM access keys
* CloudTrail
* RDS
* AWS Budgets

## Architecture

The project is structured around service-specific scanner modules and rule modules.

Each scanner collects AWS metadata using `boto3`.

Each rule module evaluates the collected metadata and returns findings with statuses such as `PASS`, `WARN`, or `FAIL`.

The combined batch runner builds a global summary, optionally persists scan
results to PostgreSQL, saves timestamped resource snapshots, and writes
human-readable and machine-readable change reports.

## Technology Stack

### Cloud

* AWS
* IAM
* S3
* EC2
* EBS
* Elastic IPs
* Security Groups
* CloudWatch Logs
* CloudTrail
* RDS

### Infrastructure and DevOps

* OpenTofu
* Docker
* Docker Compose
* Kubernetes
* kind
* GitHub Actions
* Makefile automation

### Data Engineering

* Python
* SQL
* PostgreSQL
* JSON reporting
* Markdown reporting
* Relational schema design
* Historical scan persistence

### Testing and Quality

* pytest
* OpenTofu validation workflow
* Python unit test workflow
* Redaction safety tests
* Security documentation
* Cost-safety documentation

## Security Design

The project uses a separation-of-duties model.

The Python scanner runs with a read-only scanner identity.

OpenTofu uses a separate infrastructure-management identity.

This prevents the scanner runtime identity from creating, modifying, or deleting AWS infrastructure.

The project also includes redaction safety tests to prevent accidental exposure of sensitive AWS data in public example reports.

## Infrastructure as Code

OpenTofu is used to manage selected AWS IAM infrastructure.

Current OpenTofu-managed resources include:

* Scanner read-only IAM policy
* IAM policy attachment to the scanner group

The existing scanner IAM group is referenced using a data source rather than directly recreated.

This avoids unnecessary disruption to manually created AWS identities while still allowing important infrastructure pieces to be codified.

## Local and Kubernetes Execution

The scanner can be run locally through Python, Docker Compose, or Kubernetes.

Docker Compose provides local PostgreSQL persistence.

Kubernetes support uses local `kind` for running the scanner as a Job or CronJob.

This demonstrates multiple execution models:

* Local CLI execution
* Containerised execution
* Kubernetes batch orchestration
* Scheduled Kubernetes CronJob execution

## CI/CD

The repository includes separate GitHub Actions workflows for:

* Python unit tests
* OpenTofu formatting and validation

This ensures both application code and infrastructure code are checked automatically.

## Data Model

PostgreSQL stores scan results using a normalized schema.

Core tables include:

* `scan_runs`
* `resources`
* `findings`

This allows scan history to be queried, analysed, and extended into future analytics layers.

## Example Output

The scanner produces a global summary containing:

* Overall status
* Number of services scanned
* Number of resources scanned
* Total findings
* Warning count
* Failure count
* Top risks

Example reports are stored under `examples/` using redacted data.

## Key Engineering Decisions

### Read-only scanner identity

The scanner is deliberately unable to create or modify AWS infrastructure.

This reduces the blast radius if scanner credentials are misused.

### Separate infrastructure identity

OpenTofu uses a separate infrastructure-management identity.

This mirrors production cloud environments where runtime access and deployment access are separated.

### Local-first design

The project uses local Docker, local Kubernetes, and local PostgreSQL before relying on managed AWS services.

This reduces cost and makes the project easier to reproduce.

### Rule-based scanner architecture

Each AWS service has a dedicated scanner module and rule module.

This keeps the project modular and makes it easier to add new services.

### Public repo safety

The project includes `.gitignore` rules, redacted examples, SECURITY.md, and redaction tests to reduce the risk of leaking sensitive cloud data.

## Current Outcomes

The project currently demonstrates:

* AWS governance scanning
* IAM least-privilege design
* Infrastructure as Code with OpenTofu
* Docker-based local execution
* Kubernetes Job and CronJob orchestration
* PostgreSQL persistence
* Deterministic snapshot comparison with versioned JSON change events
* Count-based retention for scheduled file output
* CI/CD validation
* Security and redaction hygiene
* Cost-safety awareness
* Automated unit testing

## Future Improvements

Planned improvements include:

* Airflow orchestration layer
* dbt Core transformation layer on PostgreSQL
* PySpark batch analytics layer
* Optional Snowflake-compatible modelling
* Additional AWS scanner coverage where it adds a defensible governance check
* Deeper analytics over historical scan data

## Summary

AWS Free-Tier Guardian is a cloud and data engineering project that demonstrates practical AWS automation, infrastructure governance, least-privilege IAM design, containerisation, Kubernetes orchestration, PostgreSQL persistence, CI/CD, and security-aware public repo practices.

The project is intentionally designed to be cost-conscious, modular, testable, and extensible.

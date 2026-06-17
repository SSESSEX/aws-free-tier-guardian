# Cost Safety Guardrails

AWS Free-Tier Guardian is designed to be a cost-conscious AWS governance project.

The project should avoid creating paid infrastructure unless a resource is explicitly planned, reviewed, and documented.

## Purpose

This document explains how the project reduces the risk of accidental AWS costs during local development, OpenTofu usage, Docker/Kubernetes testing, and future scanner expansion.

## Core Principle

The scanner should inspect AWS resources without creating or modifying them.

The Python scanner runs with a read-only AWS identity.

Infrastructure changes are managed separately through OpenTofu using an infrastructure-management identity.

## Current Cost-Safe Design

The current implementation is designed to be low-risk because it mainly uses:

* Read-only AWS API calls
* Local Docker containers
* Local Kubernetes through kind
* Local PostgreSQL
* Local report generation
* OpenTofu-managed IAM policy resources

The project does not currently create paid compute, database, storage, or networking infrastructure through OpenTofu.

## AWS Resources Managed by OpenTofu

The current OpenTofu configuration manages:

* IAM read-only policy for the scanner
* IAM policy attachment to the scanner group

IAM policies and policy attachments do not create running compute resources and do not directly generate usage-based AWS charges.

## Resources to Avoid Creating Casually

The following AWS resources can create costs and should not be added without clear planning:

* EC2 instances
* NAT Gateways
* RDS databases
* Load balancers
* Elastic IPs left unattached
* Large S3 buckets or high-volume S3 requests
* CloudWatch logs with high ingestion or no retention policy
* AWS Glue jobs
* EMR clusters
* MWAA Airflow environments
* Lambda functions with high invocation volume
* VPC endpoints
* Data transfer-heavy networking resources

## OpenTofu Safety Rules

Before running:

```bash
tofu apply
```

Always run:

```bash
tofu fmt
tofu validate
tofu plan
```

Then review the plan carefully.

Safe plans should be small, intentional, and understood before applying.

For this project, any plan that creates paid resources should be treated as a design decision, not a routine action.

## Local State Safety

OpenTofu state files must not be committed.

Do not commit:

```text
terraform.tfstate
terraform.tfstate.backup
*.tfvars
.terraform/
.tofu/
```

State files may contain AWS metadata, ARNs, account IDs, resource IDs, and environment-specific values.

## Free-Tier Development Rules

During development:

1. Prefer local containers before managed cloud services.
2. Prefer read-only AWS scanning before creating AWS resources.
3. Prefer documentation and examples before deploying paid infrastructure.
4. Prefer mocked/unit-tested rules before live integration testing.
5. Delete temporary AWS resources immediately after testing.
6. Tag all intentionally created resources.
7. Use `eu-west-2` consistently unless there is a specific reason not to.
8. Avoid long-running AWS resources unless they are explicitly required.

## Tagging Expectations

Any AWS resource intentionally created for this project should use tags such as:

```text
Project=AWSFreeTierGuardian
Environment=Dev
ManagedBy=OpenTofu
```

Tags make it easier to identify, audit, and clean up resources.

## Scanner Cost Checks

The scanner itself checks for cost and governance risks such as:

* Unattached EBS volumes
* Unassociated Elastic IPs
* Missing CloudWatch log retention
* Publicly exposed security groups
* Missing resource tags
* Disabled S3 versioning
* Missing CloudTrail trails
* RDS configuration risks

Future scanner modules should continue this cost-awareness pattern.

## Future Cost-Safety Improvements

Potential future improvements include:

* AWS Budgets scanner
* AWS Cost Explorer scanner
* Lambda scanner
* Free-tier usage documentation
* Cost anomaly detection notes
* OpenTofu cost-impact checklist
* CI checks that prevent accidental state or secret commits

## Summary

AWS Free-Tier Guardian should remain safe, explainable, and cost-conscious.

The project can grow in technical depth, but new infrastructure should be added deliberately and with clear cost awareness.

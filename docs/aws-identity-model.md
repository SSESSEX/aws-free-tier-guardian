# AWS Identity Model

AWS Free-Tier Guardian uses separate AWS identities for scanning and infrastructure management.

This separation keeps the scanner least-privilege while still allowing infrastructure to be managed through OpenTofu.

## Identity Separation

| Identity                | Purpose                                    | Permission Level                      |
| ----------------------- | ------------------------------------------ | ------------------------------------- |
| Scanner identity        | Runs the Python AWS governance scanner     | Read-only                             |
| Infrastructure identity | Runs OpenTofu to manage AWS infrastructure | Infrastructure-management permissions |

## Scanner Identity

The scanner identity is used by the Python application.

It should only have the permissions required to inspect supported AWS services, such as:

* S3 bucket configuration
* EC2 instances
* EBS volumes
* Elastic IPs
* Security groups
* CloudWatch log groups
* IAM users and access key metadata
* CloudTrail trails
* RDS DB instances

The scanner identity should not be able to create, update, or delete AWS infrastructure.

This protects the AWS account if the scanner code, local environment, or runtime credentials are ever misused.

## Infrastructure Identity

The infrastructure identity is used by OpenTofu.

It manages infrastructure resources such as IAM policies and policy attachments.

This identity is separate from the scanner identity because infrastructure management requires stronger permissions than day-to-day scanning.

## Local AWS Profiles

A typical local setup uses two AWS CLI profiles:

```text
guardian-dev  = scanner profile
sheyi-admin   = OpenTofu infrastructure profile
```

The scanner can be run with the read-only profile.

OpenTofu can be run with the infrastructure profile.

## Why This Matters

This project intentionally separates:

* Runtime access
* Infrastructure management access

This follows the principle of least privilege and mirrors how production cloud environments separate application identities from deployment or infrastructure identities.

## Security Rules

Do not commit:

* AWS access keys
* Secret access keys
* `.env` files
* `terraform.tfvars`
* OpenTofu state files
* Real AWS account IDs
* Real ARNs
* Real resource IDs from private environments

OpenTofu state files may contain sensitive AWS metadata and must remain local unless a secure remote backend is intentionally configured.

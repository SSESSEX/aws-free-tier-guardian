# OpenTofu State and Import Guide

This document explains how AWS Free-Tier Guardian handles OpenTofu state, imports, and manually-created AWS resources.

## Purpose

OpenTofu uses state to map real AWS resources to the resources defined in configuration files.

For this project, OpenTofu is used to manage selected infrastructure resources such as IAM policies and IAM policy attachments.

The Python scanner itself remains read-only and uses a separate scanner identity.

## Current State Model

This project currently uses local OpenTofu state for development.

Local state files are created after running:

```bash
tofu apply
```

Typical local state files include:

```text
terraform.tfstate
terraform.tfstate.backup
```

These files must not be committed to Git.

They may contain AWS account metadata, resource IDs, ARNs, policy attachment IDs, and other environment-specific values.

## Files That Should Be Committed

Commit OpenTofu source files such as:

```text
infra/opentofu/*.tf
infra/opentofu/README.md
infra/opentofu/.terraform.lock.hcl
```

The `.terraform.lock.hcl` file is safe to commit because it pins provider versions and helps make OpenTofu behaviour reproducible across machines.

## Files That Should Not Be Committed

Do not commit:

```text
infra/opentofu/.terraform/
infra/opentofu/.tofu/
infra/opentofu/terraform.tfstate
infra/opentofu/terraform.tfstate.backup
infra/opentofu/*.tfvars
infra/opentofu/*.tfvars.json
```

These files are local runtime files, local configuration files, or state files that may contain sensitive or environment-specific information.

## Importing Existing Resources

Some AWS resources may already exist before they are added to OpenTofu.

For example:

* IAM users created manually
* IAM groups created manually
* IAM policies created manually
* S3 buckets created manually
* Security groups created manually

OpenTofu can import these existing resources into state so that future changes can be managed as code.

The general command format is:

```bash
tofu import RESOURCE_ADDRESS RESOURCE_ID
```

Example pattern:

```bash
tofu import aws_iam_policy.example arn:aws:iam::ACCOUNT_ID_REDACTED:policy/example-policy
```

The resource address must match a resource block in the OpenTofu configuration.

## Import Workflow

When importing an existing resource:

1. Write the matching resource block in OpenTofu configuration.
2. Run `tofu fmt`.
3. Run `tofu validate`.
4. Run `tofu import RESOURCE_ADDRESS RESOURCE_ID`.
5. Run `tofu plan`.
6. Compare the plan carefully.
7. Adjust configuration until OpenTofu shows no unintended changes.
8. Commit only the `.tf` source files, not state files.

## Data Source vs Import

Not every existing resource needs to be imported.

Use a data source when the project only needs to reference an existing resource.

Use import when OpenTofu should manage the resource lifecycle.

### Data Source

A data source is suitable when the resource exists already and the project only needs to look it up.

Example:

```hcl
data "aws_iam_group" "guardian_scanner_group" {
  group_name = var.guardian_scanner_group_name
}
```

This lets OpenTofu reference the IAM group without taking ownership of the group itself.

### Import

Import is suitable when OpenTofu should become responsible for managing the resource.

Example:

```hcl
resource "aws_iam_policy" "guardian_read_only" {
  name        = var.guardian_read_only_policy_name
  description = "Least-privilege read-only policy for AWS Free-Tier Guardian scanner."
  policy      = data.aws_iam_policy_document.guardian_read_only.json
}
```

If this policy had already existed before OpenTofu managed it, it could be imported into state.

## Current Project Decision

For AWS Free-Tier Guardian:

* The read-only scanner IAM policy is managed by OpenTofu.
* The policy attachment to the scanner group is managed by OpenTofu.
* The existing scanner group is referenced using a data source.
* The scanner user remains separate and read-only.
* The infrastructure profile remains separate from the scanner profile.

This keeps the project safe and easy to reason about.

## State Safety Rules

Before committing, always check:

```bash
git status --short
```

Safe files usually look like:

```text
M  infra/opentofu/variables.tf
M  infra/opentofu/outputs.tf
A  infra/opentofu/example.tf
```

Unsafe files look like:

```text
?? infra/opentofu/terraform.tfstate
?? infra/opentofu/terraform.tfstate.backup
?? infra/opentofu/terraform.tfvars
?? infra/opentofu/.terraform/
```

Do not add unsafe files to Git.

## Useful Commands

Format OpenTofu files:

```bash
tofu fmt
```

Validate configuration:

```bash
tofu validate
```

Preview changes:

```bash
tofu plan
```

Apply approved changes:

```bash
tofu apply
```

List resources currently tracked in state:

```bash
tofu state list
```

Inspect a tracked resource:

```bash
tofu state show RESOURCE_ADDRESS
```

Import an existing resource:

```bash
tofu import RESOURCE_ADDRESS RESOURCE_ID
```

## Future Improvement

For a larger production setup, this project could move from local state to a secure remote backend with encryption, access control, and state locking.

For the current portfolio version, local state is acceptable as long as state files remain ignored and are never committed.

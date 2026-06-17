# OpenTofu Infrastructure

This directory contains OpenTofu configuration for AWS Free-Tier Guardian.

The first phase is intentionally read-only and cost-safe. It configures the AWS provider and validates that OpenTofu can connect to AWS using the local AWS CLI profile.

## Commands

Initialize OpenTofu:

```bash
tofu init
```

OpenTofu should be run with an infrastructure-management AWS profile, not the read-only scanner profile. See [`../../docs/aws-identity-model.md`](../../docs/aws-identity-model.md).
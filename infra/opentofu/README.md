# OpenTofu Infrastructure

This directory contains OpenTofu configuration for AWS Free-Tier Guardian.

The first phase is intentionally read-only and cost-safe. It configures the AWS provider and validates that OpenTofu can connect to AWS using the local AWS CLI profile.

## Commands

Initialize OpenTofu:

```bash
tofu init
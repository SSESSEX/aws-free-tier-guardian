# Snowflake deployment template

This directory contains a cost-guarded Snowflake bootstrap template for a future warehouse deployment.

## Included

- `bootstrap.sql` creates:
  - a dedicated dbt role
  - `AWS_GUARDIAN` database
  - `RAW` and `ANALYTICS` schemas
  - an XSMALL warehouse
  - a monthly resource monitor
  - least-privilege grants for dbt transformations

## Status

This script has not been executed against a Snowflake account.

It is intentionally included as a reviewed deployment design, not as evidence of a live Snowflake integration.

## Before execution

1. Review the monthly credit quota.
2. Create a dedicated dbt service user.
3. Assign the dbt role to that user.
4. Configure a local ignored Snowflake dbt profile.
5. Install the Snowflake dbt adapter.
6. Run `dbt debug` before running any transformations.

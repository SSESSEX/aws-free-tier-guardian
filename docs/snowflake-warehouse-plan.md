# Snowflake Warehouse Deployment Plan

## Status

This repository includes a Snowflake-ready deployment path, but Snowflake has not been provisioned or connected.

The current working implementation uses local PostgreSQL, dbt Core, Docker, and PySpark. The Snowflake layer is deliberately documented as a future production-style deployment option rather than presented as a completed live integration.

## Target architecture

```text
AWS scanner
    ↓
PostgreSQL operational store
    ↓
Snowflake RAW schema
    ↓
dbt staging models
    ↓
Snowflake ANALYTICS schema
    ↓
risk summary marts and reporting models
```

## Data model mapping

| Current component     | Snowflake target                                 |
| --------------------- | ------------------------------------------------ |
| `scan_runs`           | `AWS_GUARDIAN.RAW.SCAN_RUNS`                     |
| `resources`           | `AWS_GUARDIAN.RAW.RESOURCES`                     |
| `findings`            | `AWS_GUARDIAN.RAW.FINDINGS`                      |
| dbt staging models    | `AWS_GUARDIAN.ANALYTICS` views                   |
| dbt mart models       | `AWS_GUARDIAN.ANALYTICS` tables/views            |
| PySpark batch outputs | future curated datasets or external-stage inputs |

## Security model

A dedicated `AWS_GUARDIAN_DBT_ROLE` is used for transformations.

The role receives:

* warehouse usage on `AWS_GUARDIAN_XS`
* read access to the `RAW` schema
* permission to create dbt models in the `ANALYTICS` schema

The dbt connection should use environment variables or a local ignored profile file. Credentials must never be committed to Git.

## Cost guardrails

The bootstrap template uses:

* an `XSMALL` warehouse
* automatic suspension after 60 seconds of inactivity
* automatic resumption only when a query needs compute
* an initially suspended warehouse
* a monthly resource monitor with a low placeholder credit quota
* immediate warehouse suspension at 100% of the configured quota

The resource monitor quota must be reviewed before a real deployment.

## Local development versus warehouse deployment

| Layer               | Current local implementation | Future Snowflake implementation                      |
| ------------------- | ---------------------------- | ---------------------------------------------------- |
| Scanner             | Python and boto3             | Python and boto3                                     |
| Operational storage | PostgreSQL in Docker         | PostgreSQL or direct warehouse ingestion             |
| Transformation      | dbt-postgres                 | dbt-snowflake                                        |
| Batch analytics     | Local PySpark                | Snowflake tables, external stages, or Spark platform |
| Orchestration       | Airflow DAG design           | Airflow-triggered dbt and warehouse jobs             |
| Governance          | AWS scanner findings         | Scanner findings plus warehouse access controls      |

## Validation status

Validated locally:

* Python scanner and rule suite
* OpenTofu formatting and validation
* dbt models against PostgreSQL
* PySpark batch analytics job
* redaction checks
* Docker scanner workflow when Docker Desktop is running

Not yet validated:

* Snowflake credentials
* Snowflake warehouse provisioning
* dbt-snowflake connection
* Snowflake model execution
* Snowflake resource monitor behaviour

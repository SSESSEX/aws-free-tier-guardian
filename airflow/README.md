# Airflow Orchestration

This directory contains an Apache Airflow DAG for orchestrating AWS Free-Tier Guardian.

The DAG models the scanner as a data engineering workflow:

1. Validate the local environment
2. Run the AWS governance scan
3. Generate JSON and Markdown reports
4. Run redaction safety checks

## DAG

```text
airflow/dags/aws_guardian_scan_dag.py
```
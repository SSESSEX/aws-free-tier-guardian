from __future__ import annotations

import pendulum

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_ROOT = "/opt/aws-free-tier-guardian"


with DAG(
    dag_id="aws_free_tier_guardian_scan",
    description="Orchestrates AWS Free-Tier Guardian scan, reporting, and redaction checks.",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule="@daily",
    catchup=False,
    tags=["aws", "governance", "data-engineering", "portfolio"],
) as dag:
    validate_environment = BashOperator(
        task_id="validate_environment",
        bash_command=f"cd {PROJECT_ROOT} && python3 --version && python3 -m pytest tests/test_example_redactions.py",
    )

    run_guardian_scan = BashOperator(
        task_id="run_guardian_scan",
        bash_command=f"cd {PROJECT_ROOT} && python3 -m app.scanner.run_all --write-db",
    )

    generate_reports = BashOperator(
        task_id="generate_reports",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "test -f reports/aws_guardian_report.json && "
            "test -f reports/aws_guardian_report.md"
        ),
    )

    run_redaction_tests = BashOperator(
        task_id="run_redaction_tests",
        bash_command=f"cd {PROJECT_ROOT} && python3 -m pytest tests/test_example_redactions.py",
    )

    validate_environment >> run_guardian_scan >> generate_reports >> run_redaction_tests
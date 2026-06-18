from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import os

import boto3
from dotenv import load_dotenv

from app.scanner.budgets_rules import (
    evaluate_budget,
    evaluate_cost_budget_exists,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
elif not os.getenv("AWS_PROFILE"):
    print(f"Warning: .env file not found at {ENV_PATH}. Using fallback defaults.")


AWS_PROFILE = os.getenv("AWS_PROFILE", "guardian-dev")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports")

# AWS Budgets is accessed through the US East endpoint.
BUDGETS_REGION = "us-east-1"


def create_aws_session():
    """Create a boto3 session using the configured scanner profile."""
    return boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_DEFAULT_REGION,
    )


def isoformat_or_none(value):
    """Convert an AWS datetime value into JSON-safe ISO-8601 text."""
    if value is None:
        return None

    return value.isoformat()


def amount_to_float(value):
    """Convert AWS amount strings into floats for rule evaluation."""
    if value is None:
        return None

    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def extract_amount(amount_data):
    """Return a numeric amount and unit from an AWS amount object."""
    if not amount_data:
        return None, None

    return (
        amount_to_float(amount_data.get("Amount")),
        amount_data.get("Unit"),
    )


def normalize_budget(raw_budget):
    """Convert an AWS Budget response into the Guardian report format."""
    budget_limit_amount, budget_limit_unit = extract_amount(
        raw_budget.get("BudgetLimit")
    )

    calculated_spend = raw_budget.get("CalculatedSpend", {})

    actual_spend_amount, actual_spend_unit = extract_amount(
        calculated_spend.get("ActualSpend")
    )

    forecast_spend_amount, forecast_spend_unit = extract_amount(
        calculated_spend.get("ForecastedSpend")
    )

    time_period = raw_budget.get("TimePeriod", {})

    budget = {
        "budget_name": raw_budget.get("BudgetName"),
        "budget_type": raw_budget.get("BudgetType"),
        "time_unit": raw_budget.get("TimeUnit"),
        "budget_limit_amount": budget_limit_amount,
        "budget_limit_unit": budget_limit_unit,
        "actual_spend_amount": actual_spend_amount,
        "actual_spend_unit": actual_spend_unit,
        "forecast_spend_amount": forecast_spend_amount,
        "forecast_spend_unit": forecast_spend_unit,
        "has_planned_budget_limits": bool(
            raw_budget.get("PlannedBudgetLimits")
        ),
        "time_period": {
            "start": isoformat_or_none(time_period.get("Start")),
            "end": isoformat_or_none(time_period.get("End")),
        },
        "last_updated_time": isoformat_or_none(
            raw_budget.get("LastUpdatedTime")
        ),
    }

    # Only cost budgets are assessed as account-spend guardrails.
    if budget["budget_type"] == "COST":
        budget["findings"] = evaluate_budget(budget)
    else:
        budget["findings"] = []

    return budget


def list_budgets(session):
    """Read and normalize all budgets for the authenticated AWS account."""
    sts_client = session.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]

    budgets_client = session.client(
        "budgets",
        region_name=BUDGETS_REGION,
    )

    paginator = budgets_client.get_paginator("describe_budgets")

    budgets = []

    for page in paginator.paginate(
        AccountId=account_id,
        PaginationConfig={
            "PageSize": 100,
        },
    ):
        for raw_budget in page.get("Budgets", []):
            budgets.append(normalize_budget(raw_budget))

    return budgets


def build_summary(budgets):
    """Build the standard Guardian finding summary for AWS Budgets."""
    cost_budgets = [
        budget for budget in budgets
        if budget.get("budget_type") == "COST"
    ]

    account_findings = [
        evaluate_cost_budget_exists(budgets)
    ]

    all_findings = list(account_findings)

    for budget in cost_budgets:
        all_findings.extend(budget.get("findings", []))

    total_findings = 0
    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    for item in all_findings:
        total_findings += 1

        status = item.get("status")
        severity = item.get("severity")

        if status == "PASS":
            passed += 1
        elif status == "WARN":
            warnings += 1
        elif status == "FAIL":
            failed += 1
        elif status == "INFO":
            info += 1

        if severity == "CRITICAL":
            critical += 1
        elif severity == "HIGH":
            high += 1
        elif severity == "MEDIUM":
            medium += 1
        elif severity == "LOW":
            low += 1

    overall_status = "PASS"

    if failed > 0:
        overall_status = "FAIL"
    elif warnings > 0:
        overall_status = "WARN"

    return {
        "total_budgets": len(budgets),
        "cost_budget_count": len(cost_budgets),
        "non_cost_budget_count": len(budgets) - len(cost_budgets),
        "account_findings": account_findings,
        "total_findings": total_findings,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "info": info,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "overall_status": overall_status,
    }


def write_report(data):
    """Write a standalone AWS Budgets report."""
    report_dir = PROJECT_ROOT / REPORT_OUTPUT_DIR
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "budgets_scan_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return report_path


def main():
    print("Starting AWS Budgets scanner...")
    print(f"Loaded .env from: {ENV_PATH}")
    print(f"AWS profile: {AWS_PROFILE}")
    print(f"Primary AWS region: {AWS_DEFAULT_REGION}")
    print(f"AWS Budgets region: {BUDGETS_REGION}")

    session = create_aws_session()

    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()

    print("Connected to AWS successfully.")
    print(f"Using ARN: {identity.get('Arn')}")

    budgets = list_budgets(session)
    summary = build_summary(budgets)

    report = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aws_profile": AWS_PROFILE,
        "aws_region": AWS_DEFAULT_REGION,
        "budgets_region": BUDGETS_REGION,
        "budget_count": len(budgets),
        "summary": summary,
        "budgets": budgets,
    }

    report_path = write_report(report)

    print("AWS Budgets scan complete.")
    print(f"Budgets found: {len(budgets)}")
    print(f"Cost budgets found: {summary['cost_budget_count']}")
    print(f"Report written to: {report_path}")
    print(f"Overall status: {summary['overall_status']}")
    print(f"Total findings: {summary['total_findings']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Failures: {summary['failed']}")


if __name__ == "__main__":
    main()

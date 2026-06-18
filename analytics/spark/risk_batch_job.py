from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, desc
from pyspark.sql.types import StructField, StructType, StringType


RESOURCE_KEYS = [
    "bucket_name",
    "instance_id",
    "volume_id",
    "allocation_id",
    "group_id",
    "log_group_name",
    "user_name",
    "access_key_id",
    "trail_name",
    "db_instance_identifier",
    "resource_id",
]


def infer_resource_type(service: str) -> str:
    mapping = {
        "s3": "bucket",
        "ec2": "instance",
        "ebs": "volume",
        "eip": "elastic_ip",
        "security_groups": "security_group",
        "cloudwatch_logs": "log_group",
        "iam_access_keys": "access_key",
        "cloudtrail": "trail",
        "rds": "db_instance",
    }
    return mapping.get(service, "resource")


def extract_resource_id(context: dict[str, Any]) -> str:
    for key in RESOURCE_KEYS:
        value = context.get(key)
        if value:
            return str(value)
    return "account"


def collect_findings(
    obj: Any,
    service: str,
    rows: list[dict[str, str]],
    context: dict[str, Any],
) -> None:
    if isinstance(obj, dict):
        next_context = dict(context)

        for key in RESOURCE_KEYS:
            value = obj.get(key)
            if value is not None and not isinstance(value, (dict, list)):
                next_context[key] = value

        findings = obj.get("findings")
        if isinstance(findings, list):
            resource_type = str(
                obj.get("resource_type")
                or obj.get("type")
                or infer_resource_type(service)
            )
            resource_id = extract_resource_id(next_context)

            for finding in findings:
                if not isinstance(finding, dict):
                    continue

                rows.append(
                    {
                        "scan_time": str(next_context.get("scan_time", "")),
                        "service": service,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "check_name": str(
                            finding.get("check")
                            or finding.get("check_name")
                            or finding.get("rule_id")
                            or ""
                        ),
                        "status": str(finding.get("status", "UNKNOWN")).upper(),
                        "severity": str(finding.get("severity", "UNKNOWN")).upper(),
                        "message": str(finding.get("message", "")),
                    }
                )

        for value in obj.values():
            collect_findings(value, service, rows, next_context)

    elif isinstance(obj, list):
        for item in obj:
            collect_findings(item, service, rows, context)


def load_findings(input_path: Path) -> list[dict[str, str]]:
    report = json.loads(input_path.read_text(encoding="utf-8"))

    scan_time = report.get("scan_time", "")
    services = report.get("services", {})

    rows: list[dict[str, str]] = []

    for service, service_payload in services.items():
        collect_findings(
            service_payload,
            service=service,
            rows=rows,
            context={"scan_time": scan_time},
        )

    return rows


def build_schema() -> StructType:
    return StructType(
        [
            StructField("scan_time", StringType(), True),
            StructField("service", StringType(), True),
            StructField("resource_type", StringType(), True),
            StructField("resource_id", StringType(), True),
            StructField("check_name", StringType(), True),
            StructField("status", StringType(), True),
            StructField("severity", StringType(), True),
            StructField("message", StringType(), True),
        ]
    )


def run_batch_job(input_path: Path, output_dir: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input report does not exist: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_findings(input_path)

    spark = (
        SparkSession.builder.appName("aws-free-tier-guardian-risk-batch")
        .master("local[*]")
        .getOrCreate()
    )

    findings_df = spark.createDataFrame(rows, schema=build_schema())

    findings_output = output_dir / "flattened_findings"
    service_summary_output = output_dir / "service_status_summary"
    high_priority_output = output_dir / "high_priority_findings"

    findings_df.write.mode("overwrite").option("header", True).csv(
        str(findings_output)
    )

    service_summary_df = (
        findings_df.groupBy("service", "status", "severity")
        .agg(count("*").alias("finding_count"))
        .orderBy(desc("finding_count"), "service", "status", "severity")
    )

    service_summary_df.write.mode("overwrite").option("header", True).csv(
        str(service_summary_output)
    )

    high_priority_df = findings_df.filter(col("severity") == "HIGH").orderBy(
        "service", "resource_type", "check_name"
    )

    high_priority_df.write.mode("overwrite").option("header", True).csv(
        str(high_priority_output)
    )

    print(f"Input report: {input_path}")
    print(f"Findings processed: {findings_df.count()}")
    print(f"Flattened findings written to: {findings_output}")
    print(f"Service summary written to: {service_summary_output}")
    print(f"High-priority findings written to: {high_priority_output}")

    spark.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run PySpark batch analytics for AWS Free-Tier Guardian reports."
    )
    parser.add_argument(
        "--input",
        default="examples/aws_guardian_report.example.json",
        help="Path to an AWS Free-Tier Guardian JSON report.",
    )
    parser.add_argument(
        "--output",
        default="analytics/spark/output",
        help="Directory for Spark analytics outputs.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_batch_job(input_path=Path(args.input), output_dir=Path(args.output))
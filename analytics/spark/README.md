# PySpark Batch Analytics

This directory contains a local PySpark batch job for AWS Free-Tier Guardian.

The job reads an AWS Free-Tier Guardian JSON report, flattens scanner findings into a Spark DataFrame, and writes analytics outputs for downstream review.

## Purpose

This layer demonstrates how scanner output can be processed using distributed data processing patterns.

It is intentionally local-first and cost-safe. It does not create AWS Glue, EMR, or other managed Spark infrastructure.

## Input

Default input:

```text
examples/aws_guardian_report.example.json
```

A real local scan report can also be used:

```text
reports/aws_guardian_report.json
```

Generated reports under `reports/` should not be committed.

## Outputs

The batch job writes outputs under:

```text
analytics/spark/output/
```

Generated outputs include:

```text
flattened_findings/
service_status_summary/
high_priority_findings/
```

These outputs are local artifacts and should not be committed.

## Run Locally

Install Spark dependencies:

```bash
pip install -r requirements-spark.txt
```

Run the batch job against the redacted example report:

```bash
python3 analytics/spark/risk_batch_job.py \
  --input examples/aws_guardian_report.example.json \
  --output analytics/spark/output
```

## Cloud Mapping

This local PySpark job maps naturally to AWS-managed Spark services such as:

* AWS Glue
* Amazon EMR

The local version keeps the portfolio project cost-safe while demonstrating Spark-style batch analytics.

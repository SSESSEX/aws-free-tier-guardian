# AWS Free-Tier Guardian Report

## Scan Metadata

| Field          | Value                     |
| -------------- | ------------------------- |
| Scan time      | 2026-06-16T10:04:00+00:00 |
| AWS profile    | example-profile           |
| AWS region     | eu-west-2                 |
| Overall status | WARN                      |

---

## Executive Summary

| Metric            | Value |
| ----------------- | ----: |
| Services scanned  |     9 |
| Resources scanned |     4 |
| Total findings    |    20 |
| Passed            |    13 |
| Warnings          |     4 |
| Failures          |     0 |
| Info              |     3 |
| Critical severity |     0 |
| High severity     |     1 |
| Medium severity   |     1 |
| Low severity      |    18 |

---

## Resources by Service

| Service         | Resources scanned |
| --------------- | ----------------: |
| S3              |                 1 |
| EC2             |                 0 |
| EBS             |                 0 |
| Elastic IPs     |                 0 |
| Security Groups |                 2 |
| CloudWatch Logs |                 0 |
| IAM Access Keys |                 1 |
| CloudTrail      |                 0 |
| RDS             |                 0 |

---

## Service Status

| Service         | Status |
| --------------- | ------ |
| S3              | WARN   |
| EC2             | PASS   |
| EBS             | PASS   |
| Elastic IPs     | PASS   |
| Security Groups | WARN   |
| CloudWatch Logs | PASS   |
| IAM Access Keys | PASS   |
| CloudTrail      | WARN   |
| RDS             | PASS   |

---

## Top Risks

| Severity | Status | Service         | Resource type  | Resource ID        | Check                   | Message                                                                                                                          |
| -------- | ------ | --------------- | -------------- | ------------------ | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| HIGH     | WARN   | CloudTrail      | Account        | account            | CLOUDTRAIL_TRAIL_EXISTS | No CloudTrail trail was found. Consider configuring a trail for long-term audit logging.                                         |
| MEDIUM   | WARN   | S3              | Bucket         | example-dev-bucket | S3_VERSIONING           | Bucket versioning is disabled. This may be acceptable for a dev bucket, but production buckets should usually enable versioning. |
| LOW      | WARN   | Security Groups | Security Group | sg-example001      | SG_REQUIRED_TAGS        | Security group is missing recommended tags: Project and Environment.                                                             |
| LOW      | WARN   | Security Groups | Security Group | sg-example002      | SG_REQUIRED_TAGS        | Security group is missing recommended tags: Project and Environment.                                                             |

---

## Service Summaries

| Service         | Status | Total findings | Passed | Warnings | Failures | Info |
| --------------- | ------ | -------------: | -----: | -------: | -------: | ---: |
| S3              | WARN   |              6 |      5 |        1 |        0 |    0 |
| EC2             | PASS   |              0 |      0 |        0 |        0 |    0 |
| EBS             | PASS   |              0 |      0 |        0 |        0 |    0 |
| Elastic IPs     | PASS   |              0 |      0 |        0 |        0 |    0 |
| Security Groups | WARN   |             10 |      6 |        2 |        0 |    2 |
| CloudWatch Logs | PASS   |              0 |      0 |        0 |        0 |    0 |
| IAM Access Keys | PASS   |              3 |      2 |        0 |        0 |    1 |
| CloudTrail      | WARN   |              1 |      0 |        1 |        0 |    0 |
| RDS             | PASS   |              0 |      0 |        0 |        0 |    0 |

---

## Notes

This is a redacted example report. Real AWS account IDs, ARNs, access key fragments, bucket names, security group IDs, VPC IDs, subnet IDs, and environment-specific resource names have been removed or replaced with example values.

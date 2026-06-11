import os
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in .env")

    return psycopg2.connect(DATABASE_URL)


def insert_scan_run(cursor, report: dict[str, Any]) -> int:
    cursor.execute(
        """
        INSERT INTO scan_runs (scan_time, aws_profile, aws_region)
        VALUES (%s, %s, %s)
        RETURNING id;
        """,
        (
            report["scan_time"],
            report["aws_profile"],
            report["aws_region"],
        ),
    )

    return cursor.fetchone()[0]


def insert_resource(
    cursor,
    scan_run_id: int,
    service: str,
    resource_type: str,
    resource_id: str | None,
    region: str,
    raw_json: dict[str, Any],
) -> int:
    cursor.execute(
        """
        INSERT INTO resources (
            scan_run_id,
            service,
            resource_type,
            resource_id,
            region,
            raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            scan_run_id,
            service,
            resource_type,
            resource_id,
            region,
            Json(raw_json),
        ),
    )

    return cursor.fetchone()[0]


def insert_findings(cursor, db_resource_id: int, findings: list[dict[str, Any]]) -> None:
    for finding in findings:
        cursor.execute(
            """
            INSERT INTO findings (
                resource_id,
                check_name,
                status,
                severity,
                message
            )
            VALUES (%s, %s, %s, %s, %s);
            """,
            (
                db_resource_id,
                finding.get("check"),
                finding.get("status"),
                finding.get("severity"),
                finding.get("message"),
            ),
        )


def save_resource_collection(
    cursor,
    scan_run_id: int,
    service: str,
    resource_type: str,
    resources: list[dict[str, Any]],
    id_field: str,
    region: str,
) -> None:
    for resource in resources:
        cloud_resource_id = resource.get(id_field)

        db_resource_id = insert_resource(
            cursor=cursor,
            scan_run_id=scan_run_id,
            service=service,
            resource_type=resource_type,
            resource_id=cloud_resource_id,
            region=region,
            raw_json=resource,
        )

        insert_findings(
            cursor=cursor,
            db_resource_id=db_resource_id,
            findings=resource.get("findings", []),
        )


def save_report_to_postgres(report: dict[str, Any]) -> int:
    region = report["aws_region"]
    services = report["services"]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            scan_run_id = insert_scan_run(cursor, report)

            save_resource_collection(
                cursor=cursor,
                scan_run_id=scan_run_id,
                service="s3",
                resource_type="bucket",
                resources=services["s3"].get("buckets", []),
                id_field="name",
                region=region,
            )

            save_resource_collection(
                cursor=cursor,
                scan_run_id=scan_run_id,
                service="ec2",
                resource_type="instance",
                resources=services["ec2"].get("instances", []),
                id_field="instance_id",
                region=region,
            )

            save_resource_collection(
                cursor=cursor,
                scan_run_id=scan_run_id,
                service="ebs",
                resource_type="volume",
                resources=services["ebs"].get("volumes", []),
                id_field="volume_id",
                region=region,
            )

            save_resource_collection(
                cursor=cursor,
                scan_run_id=scan_run_id,
                service="eip",
                resource_type="elastic_ip",
                resources=services["eip"].get("elastic_ips", []),
                id_field="allocation_id",
                region=region,
            )

            save_resource_collection(
                cursor=cursor,
                scan_run_id=scan_run_id,
                service="security_groups",
                resource_type="security_group",
                resources=services["security_groups"].get("security_groups", []),
                id_field="group_id",
                region=region,
            )

            if "cloudwatch_logs" in services:
                save_resource_collection(
                    cursor=cursor,
                    scan_run_id=scan_run_id,
                    service="cloudwatch_logs",
                    resource_type="log_group",
                    resources=services["cloudwatch_logs"].get("log_groups", []),
                    id_field="name",
                    region=region,
                )

            if "iam_access_keys" in services:
                save_resource_collection(
                    cursor=cursor,
                    scan_run_id=scan_run_id,
                    service="iam_access_keys",
                    resource_type="access_key",
                    resources=services["iam_access_keys"].get("access_keys", []),
                    id_field="masked_access_key_id",
                    region="global",
                )

            if "cloudtrail" in services:
                save_resource_collection(
                    cursor=cursor,
                    scan_run_id=scan_run_id,
                    service="cloudtrail",
                    resource_type="trail",
                    resources=services["cloudtrail"].get("trails", []),
                    id_field="trail_name",
                    region="global",
                )

            return scan_run_id
from app.storage.postgres_writer import save_report_to_postgres


sample_report = {
    "scan_time": "2026-06-10T00:00:00+00:00",
    "aws_profile": "guardian-dev",
    "aws_region": "eu-west-2",
    "services": {
        "s3": {
            "buckets": [
                {
                    "name": "example-bucket",
                    "findings": [
                        {
                            "check": "S3_DEFAULT_ENCRYPTION",
                            "status": "PASS",
                            "severity": "LOW",
                            "message": "Bucket is encrypted.",
                        }
                    ],
                }
            ]
        },
        "ec2": {"instances": []},
        "ebs": {"volumes": []},
        "eip": {"elastic_ips": []},
        "security_groups": {"security_groups": []},
    },
}


scan_run_id = save_report_to_postgres(sample_report)

print(f"Inserted sample scan run with ID: {scan_run_id}")
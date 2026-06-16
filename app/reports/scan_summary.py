STATUS_RANK = {
    "FAIL": 3,
    "WARN": 2,
    "INFO": 1,
    "PASS": 0,
}

SEVERITY_RANK = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}

RESOURCE_CONFIG = {
    "s3": {
        "resource_key": "buckets",
        "resource_type": "bucket",
        "id_fields": ["name", "bucket_name"],
    },
    "ec2": {
        "resource_key": "instances",
        "resource_type": "instance",
        "id_fields": ["instance_id"],
    },
    "ebs": {
        "resource_key": "volumes",
        "resource_type": "volume",
        "id_fields": ["volume_id"],
    },
    "eip": {
        "resource_key": "elastic_ips",
        "resource_type": "elastic_ip",
        "id_fields": ["allocation_id", "public_ip"],
    },
    "security_groups": {
        "resource_key": "security_groups",
        "resource_type": "security_group",
        "id_fields": ["group_id", "group_name", "id", "name"],
    },
    "cloudwatch_logs": {
        "resource_key": "log_groups",
        "resource_type": "log_group",
        "id_fields": ["name", "log_group_name"],
    },
    "iam_access_keys": {
        "resource_key": "access_keys",
        "resource_type": "access_key",
        "id_fields": ["masked_access_key_id", "user_name"],
    },
    "cloudtrail": {
        "resource_key": "trails",
        "resource_type": "trail",
        "id_fields": ["trail_name", "trail_arn"],
    },
    "rds": {
        "resource_key": "db_instances",
        "resource_type": "db_instance",
        "id_fields": ["db_instance_identifier", "db_instance_arn"],
    },
}


def get_resource_identifier(resource, id_fields):
    for field in id_fields:
        value = resource.get(field)

        if value:
            return str(value)

    return "unknown"

def get_service_status(service_summary):
    explicit_status = service_summary.get("overall_status")

    if explicit_status:
        return explicit_status

    if service_summary.get("failed", 0) > 0:
        return "FAIL"

    if service_summary.get("warnings", 0) > 0:
        return "WARN"

    return "PASS"


def get_overall_status(failed, warnings):
    if failed > 0:
        return "FAIL"

    if warnings > 0:
        return "WARN"

    return "PASS"


def normalize_finding(service, resource_type, resource_id, finding):
    return {
        "service": service,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "check": finding.get("check"),
        "status": finding.get("status"),
        "severity": finding.get("severity"),
        "message": finding.get("message"),
    }


def extract_findings(services):
    findings = []

    for service_name, service_data in services.items():
        service_summary = service_data.get("summary", {})

        for account_finding in service_summary.get("account_findings", []):
            findings.append(
                normalize_finding(
                    service=service_name,
                    resource_type="account",
                    resource_id="account",
                    finding=account_finding,
                )
            )

        config = RESOURCE_CONFIG.get(service_name)

        if not config:
            continue

        resources = service_data.get(config["resource_key"], [])

        for resource in resources:
            resource_id = get_resource_identifier(
                resource=resource,
                id_fields=config["id_fields"],
            )

            for finding in resource.get("findings", []):
                findings.append(
                    normalize_finding(
                        service=service_name,
                        resource_type=config["resource_type"],
                        resource_id=resource_id,
                        finding=finding,
                    )
                )

    return findings


def sort_risks(findings):
    risk_findings = [
        finding for finding in findings
        if finding.get("status") in {"FAIL", "WARN"}
    ]

    return sorted(
        risk_findings,
        key=lambda finding: (
            STATUS_RANK.get(finding.get("status"), 0),
            SEVERITY_RANK.get(finding.get("severity"), 0),
            finding.get("service") or "",
        ),
        reverse=True,
    )


def count_resources(services):
    total = 0
    by_service = {}

    for service_name, service_data in services.items():
        config = RESOURCE_CONFIG.get(service_name)

        if not config:
            by_service[service_name] = 0
            continue

        count = len(service_data.get(config["resource_key"], []))
        by_service[service_name] = count
        total += count

    return total, by_service


def build_global_summary(services):
    resources_scanned, resources_by_service = count_resources(services)

    findings = extract_findings(services)
    top_risks = sort_risks(findings)

    passed = 0
    warnings = 0
    failed = 0
    info = 0
    critical = 0
    high = 0
    medium = 0
    low = 0

    services_by_status = {}

    for service_name, service_data in services.items():
        service_summary = service_data.get("summary", {})
        services_by_status[service_name] = get_service_status(service_summary)

    for finding in findings:
        status = finding.get("status")
        severity = finding.get("severity")

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

    return {
        "overall_status": get_overall_status(
            failed=failed,
            warnings=warnings,
        ),
        "services_scanned": len(services),
        "resources_scanned": resources_scanned,
        "resources_by_service": resources_by_service,
        "services_by_status": services_by_status,
        "total_findings": len(findings),
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "info": info,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "top_risks": top_risks[:10],
    }
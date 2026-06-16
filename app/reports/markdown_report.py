from pathlib import Path


def safe(value):
    if value is None:
        return ""

    return str(value)


def markdown_table(headers, rows):
    lines = []

    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows:
        lines.append("| " + " | ".join(safe(value) for value in row) + " |")

    return "\n".join(lines)


def build_resources_by_service_table(summary):
    resources_by_service = summary.get("resources_by_service", {})

    rows = [
        [service, count]
        for service, count in resources_by_service.items()
    ]

    return markdown_table(
        headers=["Service", "Resources scanned"],
        rows=rows,
    )


def build_services_by_status_table(summary):
    services_by_status = summary.get("services_by_status", {})

    rows = [
        [service, status]
        for service, status in services_by_status.items()
    ]

    return markdown_table(
        headers=["Service", "Status"],
        rows=rows,
    )


def build_top_risks_table(summary):
    top_risks = summary.get("top_risks", [])

    if not top_risks:
        return "No FAIL or WARN findings detected."

    rows = []

    for risk in top_risks:
        rows.append(
            [
                risk.get("severity"),
                risk.get("status"),
                risk.get("service"),
                risk.get("resource_type"),
                risk.get("resource_id"),
                risk.get("check"),
                risk.get("message"),
            ]
        )

    return markdown_table(
        headers=[
            "Severity",
            "Status",
            "Service",
            "Resource type",
            "Resource ID",
            "Check",
            "Message",
        ],
        rows=rows,
    )


def build_service_summary_table(services):
    rows = []

    for service_name, service_data in services.items():
        summary = service_data.get("summary", {})

        rows.append(
            [
                service_name,
                summary.get("overall_status", "PASS"),
                summary.get("total_findings", 0),
                summary.get("passed", 0),
                summary.get("warnings", 0),
                summary.get("failed", 0),
                summary.get("info", 0),
            ]
        )

    return markdown_table(
        headers=[
            "Service",
            "Status",
            "Total findings",
            "Passed",
            "Warnings",
            "Failures",
            "Info",
        ],
        rows=rows,
    )


def build_markdown_report(report):
    summary = report.get("summary", {})
    services = report.get("services", {})

    lines = [
        "# AWS Free-Tier Guardian Report",
        "",
        "## Scan metadata",
        "",
        markdown_table(
            headers=["Field", "Value"],
            rows=[
                ["Scan time", report.get("scan_time")],
                ["AWS profile", report.get("aws_profile")],
                ["AWS region", report.get("aws_region")],
                ["Overall status", summary.get("overall_status")],
            ],
        ),
        "",
        "## Executive summary",
        "",
        markdown_table(
            headers=["Metric", "Value"],
            rows=[
                ["Services scanned", summary.get("services_scanned")],
                ["Resources scanned", summary.get("resources_scanned")],
                ["Total findings", summary.get("total_findings")],
                ["Passed", summary.get("passed")],
                ["Warnings", summary.get("warnings")],
                ["Failures", summary.get("failed")],
                ["Info", summary.get("info")],
                ["Critical severity", summary.get("critical")],
                ["High severity", summary.get("high")],
                ["Medium severity", summary.get("medium")],
                ["Low severity", summary.get("low")],
            ],
        ),
        "",
        "## Resources by service",
        "",
        build_resources_by_service_table(summary),
        "",
        "## Service status",
        "",
        build_services_by_status_table(summary),
        "",
        "## Top risks",
        "",
        build_top_risks_table(summary),
        "",
        "## Service summaries",
        "",
        build_service_summary_table(services),
        "",
    ]

    return "\n".join(lines)


def write_markdown_report(report, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    report_path = output_path / "aws_guardian_report.md"

    with open(report_path, "w", encoding="utf-8") as file:
        file.write(build_markdown_report(report))

    return report_path
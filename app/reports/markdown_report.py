from pathlib import Path


def write_markdown_report(report, output_path):
    """Write a human-readable Markdown version of the scan report."""
    output_path = Path(output_path)

    lines = []

    lines.append("# AWS Free-Tier Guardian Report")
    lines.append("")
    lines.append(f"**Scan time:** {report.get('scan_time')}")
    lines.append(f"**AWS profile:** `{report.get('aws_profile')}`")
    lines.append(f"**AWS region:** `{report.get('aws_region')}`")
    lines.append(f"**Bucket count:** {report.get('bucket_count')}")
    lines.append("")

    summary = report.get("summary", {})

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Overall status:** `{summary.get('overall_status')}`")
    lines.append(f"- **Total findings:** {summary.get('total_findings')}")
    lines.append(f"- **Passed:** {summary.get('passed')}")
    lines.append(f"- **Warnings:** {summary.get('warnings')}")
    lines.append(f"- **Failed:** {summary.get('failed')}")
    lines.append(f"- **Critical:** {summary.get('critical')}")
    lines.append(f"- **High:** {summary.get('high')}")
    lines.append(f"- **Medium:** {summary.get('medium')}")
    lines.append(f"- **Low:** {summary.get('low')}")
    lines.append("")

    lines.append("## Buckets")
    lines.append("")

    for bucket in report.get("buckets", []):
        lines.append(f"### `{bucket.get('name')}`")
        lines.append("")
        lines.append(f"- **Region:** `{bucket.get('region')}`")
        lines.append(f"- **Created:** `{bucket.get('creation_date')}`")
        lines.append(f"- **Policy public:** `{bucket.get('policy_status', {}).get('is_public')}`")
        lines.append(f"- **Versioning:** `{bucket.get('versioning', {}).get('status')}`")
        lines.append(f"- **Encryption:** `{bucket.get('encryption', {}).get('algorithm')}`")
        lines.append(f"- **Object ownership:** `{bucket.get('ownership_controls', {}).get('object_ownership')}`")
        lines.append("")

        lines.append("#### Findings")
        lines.append("")

        for finding in bucket.get("findings", []):
            lines.append(
                f"- **{finding.get('status')}** "
                f"`{finding.get('check')}` "
                f"({finding.get('severity')}): {finding.get('message')}"
            )

        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path
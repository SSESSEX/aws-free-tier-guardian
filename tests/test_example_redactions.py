import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"

REQUIRED_EXAMPLE_FILES = [
    EXAMPLES_DIR / "aws_guardian_report.example.json",
    EXAMPLES_DIR / "aws_guardian_report.example.md",
    EXAMPLES_DIR / "snapshot-monitoring" / "aws-config-before.example.json",
    EXAMPLES_DIR / "snapshot-monitoring" / "aws-config-after.example.json",
    EXAMPLES_DIR / "snapshot-monitoring" / "aws-config-diff.example.md",
]

EXAMPLE_FILES = sorted(
    path
    for path in EXAMPLES_DIR.rglob("*")
    if path.is_file() and path.suffix in {".json", ".md"}
)


FORBIDDEN_PATTERNS = [
    r"\b\d{12}\b",                    # AWS account IDs
    r"arn:aws:",                      # Real AWS ARNs
    r"AKIA(?!\*+EXAMPLE)",            # Real-looking AWS access key IDs
    r"77\.101\.",                     # Your previous public IP range
    r"sheyi",                         # Personal/resource naming
    r"sheyishoyebi",                  # Personal/resource naming
    r"guardian-dev",                  # Real local AWS profile
    r"aws-free-tier-guardian-dev",    # Real IAM username
]


def test_example_report_files_exist():
    for file_path in REQUIRED_EXAMPLE_FILES:
        assert file_path.exists(), f"Missing example file: {file_path}"


def test_example_reports_do_not_contain_sensitive_values():
    for file_path in EXAMPLE_FILES:
        content = file_path.read_text(encoding="utf-8")

        for pattern in FORBIDDEN_PATTERNS:
            assert not re.search(pattern, content, re.IGNORECASE), (
                f"Sensitive-looking pattern found in {file_path}: {pattern}"
            )


def test_example_reports_only_use_redacted_security_group_ids():
    for file_path in EXAMPLE_FILES:
        content = file_path.read_text(encoding="utf-8")

        real_sg_ids = re.findall(r"\bsg-[0-9a-f]{8,17}\b", content)

        assert real_sg_ids == [], (
            f"Real-looking security group IDs found in {file_path}: {real_sg_ids}"
        )


def test_example_reports_only_use_redacted_vpc_ids():
    for file_path in EXAMPLE_FILES:
        content = file_path.read_text(encoding="utf-8")

        real_vpc_ids = re.findall(r"\bvpc-[0-9a-f]{8,17}\b", content)

        assert real_vpc_ids == [], (
            f"Real-looking VPC IDs found in {file_path}: {real_vpc_ids}"
        )


def test_example_reports_only_use_redacted_subnet_ids():
    for file_path in EXAMPLE_FILES:
        content = file_path.read_text(encoding="utf-8")

        real_subnet_ids = re.findall(r"\bsubnet-[0-9a-f]{8,17}\b", content)

        assert real_subnet_ids == [], (
            f"Real-looking subnet IDs found in {file_path}: {real_subnet_ids}"
        )

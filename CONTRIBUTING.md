# Contributing

AWS Free-Tier Guardian is a read-only AWS governance scanner. Contributions should preserve the project’s security-first and least-privilege design.

## Development Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the test suite:

```bash
python3 -m pytest
```

## Local Environment

Create a local `.env` file based on `.env.example`.

Do not commit `.env`.

Required local values include:

```text
AWS_PROFILE
AWS_DEFAULT_REGION
REPORT_OUTPUT_DIR
DATABASE_URL
```

## Adding a New Scanner

When adding a new AWS service scanner:

1. Add the scanner module under `app/scanner/`.
2. Add the rule module under `app/scanner/`.
3. Add unit tests under `tests/`.
4. Add the scanner to `app/scanner/run_all.py`.
5. Add PostgreSQL persistence support in `app/storage/postgres_writer.py` if the service returns resources.
6. Add the service to global summary handling in `app/reports/scan_summary.py`.
7. Update the README if the new scanner changes project coverage.

## Testing Expectations

All rule logic should be unit tested.

Run:

```bash
python3 -m pytest
```

Docker validation:

```bash
docker compose build scanner
docker compose run --rm scanner python -m pytest
```

## Security and Redaction

Do not commit:

* Real AWS credentials
* `.env` files
* Generated reports from `reports/`
* Real AWS account IDs
* Real ARNs
* Real VPC IDs, subnet IDs, security group IDs, or public IPs in example reports
* Real database passwords

Example reports must be redacted before commit.

Run redaction safety tests:

```bash
python3 -m pytest tests/test_example_redactions.py
```

## Commit Style

Use short, descriptive commit messages.

Examples:

```text
Add RDS governance scanner
Add CloudTrail rule tests
Add redacted example reports
Polish Kubernetes documentation
```

# Security Policy

AWS Free-Tier Guardian is designed as a read-only AWS governance scanner.

The project follows a least-privilege approach and does not create, modify, start, stop, rotate, or delete AWS resources. Scanner access is intended to be granted through narrowly scoped IAM policies for each supported AWS service.

## Sensitive Data Handling

The following files and values must not be committed:

* `.env`
* Real AWS access keys
* AWS secret access keys
* Real AWS account IDs
* Unredacted ARNs
* Real VPC IDs, subnet IDs, security group IDs, or resource identifiers in public example files
* Real database passwords
* Generated reports from the local `reports/` directory

The project includes redacted example reports under:

```text
examples/
```

These files are safe demonstration outputs and should not contain real AWS identifiers.

## Redaction Safety Tests

The test suite includes checks to prevent accidental exposure of sensitive-looking values in example reports.

Run:

```bash
python3 -m pytest tests/test_example_redactions.py
```

The full test suite can be run with:

```bash
python3 -m pytest
```

## AWS Credentials

AWS credentials should be supplied locally through the AWS CLI profile system or mounted into a local Kubernetes Secret for development.

Do not commit AWS credentials, `.env` files, or local AWS config files.

## Reporting a Security Issue

This is a personal portfolio project. If you notice a potential exposure or unsafe example value, open an issue or contact the repository owner directly.

.PHONY: test redaction-check scan scan-db docker-build docker-test docker-scan k8s-load k8s-manual-scan k8s-manual-logs k8s-delete-manual

test:
	python3 -m pytest

redaction-check:
	python3 -m pytest tests/test_example_redactions.py

scan:
	python3 -m app.scanner.run_all

scan-db:
	python3 -m app.scanner.run_all --write-db

docker-build:
	docker compose build scanner

docker-test:
	docker compose run --rm scanner python -m pytest

docker-scan:
	docker compose run --rm scanner python -m app.scanner.run_all --write-db

k8s-load:
	docker build -t aws-free-tier-guardian-scanner:local .
	kind load docker-image aws-free-tier-guardian-scanner:local --name aws-guardian

k8s-manual-scan:
	kubectl -n aws-guardian create job manual-guardian-scan --from=cronjob/aws-guardian-scan

k8s-manual-logs:
	kubectl -n aws-guardian logs job/manual-guardian-scan

k8s-delete-manual:
	kubectl -n aws-guardian delete job manual-guardian-scan

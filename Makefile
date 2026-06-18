.PHONY: test redaction-check scan scan-db docker-build docker-test docker-scan k8s-load k8s-manual-scan k8s-manual-logs k8s-delete-manual tofu-fmt tofu-validate tofu-plan tofu-check validate-local validate-full dbt-debug dbt-run dbt-test dbt-check spark-run spark-check

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
tofu-fmt:
	cd infra/opentofu && tofu fmt

tofu-validate:
	cd infra/opentofu && tofu validate

tofu-plan:
	cd infra/opentofu && tofu plan

tofu-check:
	cd infra/opentofu && tofu fmt -check
	cd infra/opentofu && tofu validate


validate-local:
	$(MAKE) tofu-check
	$(MAKE) test
	$(MAKE) redaction-check

validate-full:
	$(MAKE) tofu-check
	$(MAKE) test
	$(MAKE) redaction-check
	$(MAKE) docker-build
	$(MAKE) docker-test


dbt-debug:
	cd analytics/dbt && DBT_PROFILES_DIR=. dbt debug

dbt-run:
	cd analytics/dbt && DBT_PROFILES_DIR=. dbt run

dbt-test:
	cd analytics/dbt && DBT_PROFILES_DIR=. dbt test

dbt-check:
	cd analytics/dbt && DBT_PROFILES_DIR=. dbt debug
	cd analytics/dbt && DBT_PROFILES_DIR=. dbt run
	cd analytics/dbt && DBT_PROFILES_DIR=. dbt test
    
spark-run:
	python3 analytics/spark/risk_batch_job.py --input examples/aws_guardian_report.example.json --output analytics/spark/output

spark-check:
	$(MAKE) spark-run

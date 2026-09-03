import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KUBERNETES_DIR = PROJECT_ROOT / "k8s"
SCANNER_WORKLOADS = [
    KUBERNETES_DIR / "scanner-job.yaml",
    KUBERNETES_DIR / "scanner-cronjob.yaml",
]

UNIFIED_BATCH_COMMAND = re.compile(
    r"command:\s*"
    r"- python\s*"
    r"- -m\s*"
    r"- app\.snapshots\.run_guardian_batch\s*"
    r"- --write-db"
)

PERSISTENT_REPORTS_VOLUME = re.compile(
    r"- name: reports\s*"
    r"persistentVolumeClaim:\s*"
    r"claimName: guardian-reports-pvc"
)


@pytest.mark.parametrize("manifest_path", SCANNER_WORKLOADS)
def test_scanner_workloads_run_unified_persistent_batch(manifest_path):
    manifest = manifest_path.read_text(encoding="utf-8")

    assert UNIFIED_BATCH_COMMAND.search(manifest)
    assert "app.scanner.run_all" not in manifest
    assert PERSISTENT_REPORTS_VOLUME.search(manifest)
    assert "emptyDir:" not in manifest
    assert "mountPath: /app/reports" in manifest


def test_scanner_cronjob_prevents_overlapping_snapshot_runs():
    manifest = (KUBERNETES_DIR / "scanner-cronjob.yaml").read_text(
        encoding="utf-8"
    )

    assert "concurrencyPolicy: Forbid" in manifest


def test_scanner_cronjob_enables_bounded_snapshot_retention():
    manifest = (KUBERNETES_DIR / "scanner-cronjob.yaml").read_text(
        encoding="utf-8"
    )

    assert re.search(r'- --retention-count\s*- "672"', manifest)


def test_standalone_job_does_not_enable_retention_implicitly():
    manifest = (KUBERNETES_DIR / "scanner-job.yaml").read_text(encoding="utf-8")

    assert "--retention-count" not in manifest


def test_reports_pvc_is_separate_from_postgres_storage():
    reports_pvc = (KUBERNETES_DIR / "reports-pvc.yaml").read_text(
        encoding="utf-8"
    )
    postgres_pvc = (KUBERNETES_DIR / "postgres-pvc.yaml").read_text(
        encoding="utf-8"
    )

    assert "kind: PersistentVolumeClaim" in reports_pvc
    assert "name: guardian-reports-pvc" in reports_pvc
    assert "namespace: aws-guardian" in reports_pvc
    assert "ReadWriteOnce" in reports_pvc
    assert "storage: 1Gi" in reports_pvc
    assert "name: guardian-reports-pvc" not in postgres_pvc
    assert "name: guardian-postgres-pvc" in postgres_pvc

#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT_DIR="${PROJECT_ROOT}/reports/snapshots"
DIFF_REPORT_DIR="${PROJECT_ROOT}/reports/snapshot-diffs"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1 && [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Error: Python interpreter not found: ${PYTHON_BIN}" >&2
    exit 1
fi

cd "${PROJECT_ROOT}"

echo "Starting AWS Free-Tier Guardian batch monitor..."
echo "Project root: ${PROJECT_ROOT}"
echo "Python: ${PYTHON_BIN}"
echo

"${PYTHON_BIN}" -m app.snapshots.run_guardian_batch "$@"

echo
echo "Batch monitoring completed successfully."
echo "Snapshots directory: ${SNAPSHOT_DIR}"
echo "Diff reports directory: ${DIFF_REPORT_DIR}"

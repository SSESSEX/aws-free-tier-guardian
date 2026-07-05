#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="${PROJECT_ROOT}/reports"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1 && [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Error: Python interpreter not found: ${PYTHON_BIN}" >&2
    exit 1
fi

mkdir -p "${REPORTS_DIR}"

cd "${PROJECT_ROOT}"

echo "Starting AWS Free-Tier Guardian scan..."
echo "Project root: ${PROJECT_ROOT}"
echo "Python: ${PYTHON_BIN}"
echo "AWS profile: ${AWS_PROFILE:-default}"
echo

"${PYTHON_BIN}" -m app.scanner.run_all "$@"

echo
echo "Scan completed successfully."
echo "Reports written to: ${REPORTS_DIR}"
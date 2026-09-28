#!/usr/bin/env bash
# Run the Obj C Python test suite.
# Usage (from obj-c/):
#   ./run-all-tests.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

echo "==> unittest"
"$PY" -m unittest discover -s tests -v
echo "==> all tests finished"

#!/usr/bin/env bash
# Run the Obj C Python test suite.
# Usage (from obj-c/):
#   ./run-all-tests.sh
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x ../../../.venv/bin/python ]]; then
  PY=../../../.venv/bin/python
elif [[ -f ../../../.venv/Scripts/python.exe ]]; then
  PY=../../../.venv/Scripts/python.exe
else
  PY=python3
  command -v "$PY" >/dev/null 2>&1 || PY=python
fi

echo "==> Obj C tests (including histogram and scatter plots)"
"$PY" -m unittest discover -s tests -v
echo "==> all tests finished"

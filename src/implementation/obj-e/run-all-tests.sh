#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

"$PY" -m unittest discover -s tests -v

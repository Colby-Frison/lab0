#!/usr/bin/env bash
# Create a workload + multi-queue config, then run multi-queue-sim.
# Usage:
#   ./scripts/run-queue.sh
#   QUEUES=3 INTERVAL=0:9 DIST=fixed FIXED_WORK=20 ./scripts/run-queue.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MAKER="$ROOT/tooling/make-queue-inputs/make_queue_inputs.py"
OUT_DIR="${OUT_DIR:-$ROOT/runs/queue}"
QUEUES="${QUEUES:-2}"
INTERVAL="${INTERVAL:-0:9}"
DIST="${DIST:-fixed}"
SEED="${SEED:-42}"
FIXED_WORK="${FIXED_WORK:-20}"
FIXED_TASKS="${FIXED_TASKS:-1}"
FIXED_JOBS="${FIXED_JOBS:-1}"
LAM="${LAM:-1.5}"
mkdir -p "$OUT_DIR"

echo "==> 1/2 Create workload and config"
python3 "$MAKER" \
  --out-dir "$OUT_DIR" \
  --queues "$QUEUES" \
  --interval "$INTERVAL" \
  --dist "$DIST" \
  --seed "$SEED" \
  --fixed-work "$FIXED_WORK" \
  --fixed-tasks "$FIXED_TASKS" \
  --fixed-jobs "$FIXED_JOBS" \
  --lam "$LAM"

BIN="$ROOT/build/multi-queue-sim"
if [[ ! -x "$BIN" && ! -f "${BIN}.exe" ]]; then
  echo "Building multi-queue-sim..."
  cmake -S "$ROOT" -B "$ROOT/build"
  cmake --build "$ROOT/build"
fi
if [[ -f "${BIN}.exe" ]]; then
  BIN="${BIN}.exe"
fi

echo "==> 2/2 Run multi-queue-sim"
(
  cd "$OUT_DIR"
  "$BIN" --config "$OUT_DIR/qconf.csv" --qmet "$OUT_DIR/qmet.csv" --events "$OUT_DIR/events.log"
)

echo "Done. Artifacts in $OUT_DIR:"
ls -la "$OUT_DIR"

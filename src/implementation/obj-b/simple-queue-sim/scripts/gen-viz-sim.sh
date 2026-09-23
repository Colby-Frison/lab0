#!/usr/bin/env bash
# Generate a workload (Obj A), visualize it, then run simple-queue-sim.
# Usage:
#   ./scripts/gen-viz-sim.sh
# Optional env overrides:
#   INTERVAL=0:29 DIST=poisson LAM=1.5 SEED=42 TASK_MODE=fixed FIXED_TASKS=2 FIXED_WORK=10

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/../../../../" && pwd)"
GEN="$REPO/src/implementation/obj-a/workload-generator/workload_generator.py"
VIZ="$REPO/src/implementation/obj-a/workload-visualizer/workload_visualizer.py"
OUT_DIR="${OUT_DIR:-$ROOT/runs/pipeline}"
mkdir -p "$OUT_DIR"

INTERVAL="${INTERVAL:-0:29}"
DIST="${DIST:-poisson}"
LAM="${LAM:-1.5}"
SEED="${SEED:-42}"
TASK_MODE="${TASK_MODE:-fixed}"
FIXED_TASKS="${FIXED_TASKS:-2}"
FIXED_WORK="${FIXED_WORK:-10}"

WL="$OUT_DIR/in0.wl"
HIST="$OUT_DIR/hist_arrival.png"
SCAT="$OUT_DIR/scat_arrival_tasks.png"
SINK="$OUT_DIR/out0.wl"
QMET="$OUT_DIR/qmet.csv"
EVENTS="$OUT_DIR/events.log"
CONF="$OUT_DIR/qconf.csv"

echo "==> 1/3 Generate workload"
python3 "$GEN" \
  --interval "$INTERVAL" \
  --dist "$DIST" \
  --lam "$LAM" \
  --seed "$SEED" \
  --task-mode "$TASK_MODE" \
  --fixed-tasks "$FIXED_TASKS" \
  --fixed-work "$FIXED_WORK" \
  --out "$WL"

echo "==> 2/3 Visualize workload"
python3 "$VIZ" "$WL" --hist "arrival time" --bins 15 \
  --title "Arrivals ($DIST)" --out "$HIST"
python3 "$VIZ" "$WL" --scat "arrival time,Job Id" \
  --title "Jobs over time" --out "$SCAT"

WL_ABS="$(cd "$(dirname "$WL")" && pwd)/$(basename "$WL")"
cat > "$CONF" <<EOF
Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
q0,64,1,Sub-10*,10,$WL_ABS,$SINK,[],[]
EOF

BIN="$ROOT/build/simple-queue-sim"
if [[ ! -x "$BIN" && ! -f "${BIN}.exe" ]]; then
  echo "Building simple-queue-sim..."
  cmake -S "$ROOT" -B "$ROOT/build"
  cmake --build "$ROOT/build"
fi
if [[ -f "${BIN}.exe" ]]; then
  BIN="${BIN}.exe"
fi

echo "==> 3/3 Run simulator"
(cd "$OUT_DIR" && "$BIN" --config "$CONF" --qmet "$QMET" --events "$EVENTS")

echo "Done. Artifacts in $OUT_DIR:"
ls -la "$OUT_DIR"

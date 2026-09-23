#!/usr/bin/env bash
# Run simple-queue-sim on an existing Obj A workload CSV.
# Usage:
#   ./scripts/run-existing.sh [WORKLOAD_CSV] [OUT_DIR]
#
# Defaults to examples/obj-a/wl-uniform.csv

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/../../../../" && pwd)"

WL="${1:-$REPO/src/examples/obj-a/wl-uniform.csv}"
OUT_DIR="${2:-$ROOT/runs/existing}"
mkdir -p "$OUT_DIR"

if [[ ! -f "$WL" ]]; then
  echo "workload not found: $WL" >&2
  exit 1
fi

# Resolve absolute paths for config Source/Sink (sim opens relative to cwd)
WL_ABS="$(cd "$(dirname "$WL")" && pwd)/$(basename "$WL")"
SINK="$OUT_DIR/out0.wl"
QMET="$OUT_DIR/qmet.csv"
EVENTS="$OUT_DIR/events.log"
CONF="$OUT_DIR/qconf.csv"

# Prefer Sub-10* so multi-task jobs drain to the sink (PDF Section B policy).
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

echo "Workload: $WL_ABS"
echo "Config:   $CONF"
(cd "$OUT_DIR" && "$BIN" --config "$CONF" --qmet "$QMET" --events "$EVENTS")

echo "Wrote:"
echo "  $SINK"
echo "  $QMET"
echo "  $EVENTS"

# Objective C — Implementation

Python analysis tools that consume the Obj B / Obj E simulator outputs
(`events.log`, `qmet.csv`). Design notes live in
[`src/design/obj-c/`](../../design/obj-c/README.md).

| Tool | Directory | Entry point | Input → Output | Status |
|------|-----------|-------------|----------------|--------|
| Derive system metrics | `derive-sys-metrics/` | `derive_sys_metrics.py` | `events.log` → `sysmetrics.csv` | Implemented |
| Plot system metrics | `plot-sys-metrics/` | `plot_sys_metrics.py` | `sysmetrics.csv` → `resplot.png` | Implemented |
| Derive event (job) metrics | `derive-event-metrics/` | `derive_event_metrics.py` | `events.log` → `emetrics.csv` | Implemented |
| Plot event metrics | `plot-derive-event-metrics/` | `plot_derive_event_metrics.py` | `emetrics.csv` → `png` | Implemented |
| Filter by queue / by job | `filters/` | — | `qmet.csv` / `events.log` → subset | Not started |
| Compute USE / plot USE | `USE/` | — | `qmet.csv` → `quse.csv` → `use.png` | Not started |
| Create event trace | `create-etrace/` | — | `events.log` → `etrace.png` | Not started |

See each subdirectory README for CLI details and metric definitions.

## Quick start

```bash
cd src/implementation/obj-c

# System view: end-to-end response time percentiles + throughput per time step
python derive-sys-metrics/derive_sys_metrics.py \
  --events ../obj-b/simple-queue-sim/runs/pipeline/events.log \
  --out /tmp/sysmetrics.csv --window 10 --dense
python plot-sys-metrics/plot_sys_metrics.py \
  --sysmetrics /tmp/sysmetrics.csv --out /tmp/resplot.png --title "Poisson workload"

# Job view: one row per (job, queue) visit
python derive-event-metrics/derive_event_metrics.py \
  --events ../obj-b/simple-queue-sim/runs/pipeline/events.log --out /tmp/emetrics.csv
```

Requires Python 3 with `numpy`, `pandas`, and `matplotlib`.

## Tests

```bash
python -m unittest discover -s tests -v
# or
./run-all-tests.sh        # Linux / Git Bash / WSL
.\run-all-tests.ps1       # Windows PowerShell
```

Fixtures under `tests/fixtures/` are the PDF walkthrough log, a two-queue transfer
log, and a `QUEUE-FULL` log.

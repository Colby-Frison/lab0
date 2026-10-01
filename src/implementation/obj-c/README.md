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
| Filter by queue | `filter-by-queue/` | `filter_by_queue.py` | `qmet.csv` → `qmet.csv` subset | Implemented |
| Filter by job | `filter-by-job/` | `filter_by_job.py` | `events.log` → `events.log` subset | Implemented |
| Compute USE | `compute-use/` | `compute_use.py` | `qmet.csv` + config → `quse.csv` | Implemented |
| Plot USE | `plot-use/` | `plot_use.py` | `quse.csv` → `use.png` | Implemented |
| Create event trace | `create-event-trace/` | `create_event_trace.py` | `events.log` → `etrace.png` | Implemented |

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

# Queue view: keep only the qmet rows of queue 0 (or a list: --qid 0,2)
python filter-by-queue/filter_by_queue.py \
  --qmet ../obj-b/simple-queue-sim/runs/pipeline/qmet.csv --qid 0 --out /tmp/q0_metrics.csv

# Trace one job: keep only the event-log lines of j0 (or a list: --jobs 0,1)
python filter-by-job/filter_by_job.py \
  --events ../obj-b/simple-queue-sim/runs/pipeline/events.log --jobs 0 --out /tmp/j0_events.log

# USE: utilization, waiting jobs, and errors over 10 / 100 / 1000 steps
python compute-use/compute_use.py \
  --qmet ../obj-b/simple-queue-sim/runs/pipeline/qmet.csv \
  --config ../../examples/obj-b/simple-queue-config-ex.csv --out /tmp/quse.csv
python plot-use/plot_use.py --quse /tmp/quse.csv --out /tmp/use.png
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
log, a `QUEUE-FULL` log, and a three-queue `qmet-multi.csv`.

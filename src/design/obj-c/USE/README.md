# USE Metrics: Compute and Plot

## Goal

Given the queue metrics log (`qmet.csv`), compute the USE (Utilization, Saturation, Errors) metrics for the system and emit them to a synthetic summary file (`quse.csv`). Then, given the computed USE metrics, generate a clear visualization (`quse.png`) to analyze system health and capacity constraints over time.

## CLI sketch

All parameters are command-line arguments (required + optional), allowing these to be run as sequential pipeline steps:

```bash
# 1. Compute the metrics
compute-use \
  --qmet qmet.csv \
  --config qconf.csv \
  [--out quse.csv]            # default: quse.csv

# 2. Generate the visual
plot-use \
  --quse quse.csv \
  [--out quse.png]            # default: quse.png

```

Notes:

* `--config` is required for `compute-use` to determine the maximum capacity (number of servers and max queue size) needed to calculate utilization and saturation ratios.
* `plot-use` assumes `quse.csv` is correctly formatted and relies on Matplotlib to handle the rendering.

## USE Metric Definitions

Align with standard systems analysis methodology for the queueing simulator:

| Metric | Derivation from `qmet.csv` & config | Insight |
| --- | --- | --- |
| **Utilization** | `num-jobs-in-service` / `Num. Servers` | What percentage of the processing capacity is actively busy? |
| **Saturation** | `num-jobs-in-queue` (% of `Queue Max Size`) | How much excess work is waiting because servers are full? |
| **Errors** | `num-of-errors` | How many jobs were rejected due to the waiting queue being full? |

Suggested mapping for `quse.csv`:
Generate a time-series output where each row represents a time step, and the columns contain the derived USE percentages, enabling easy line-graph plotting.

## Worked example (tiny)

Input `qmet.csv` (assuming config specifies 2 Servers, Max Queue Size 4):
```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,0,1,0
1,0,2,2,0
2,0,4,2,1
```

Possible `quse.csv` output:
```csv
time-step,Utilization(10),Saturation(10),Errors(10),...
0,0.5,0.0,0
1,1.0,0.5,0
2,1.0,1.0,1
```

## Implementation plan

1. Parse CLI parameters for both scripts.
2. In `compute-use`, ingest `qmet.csv` and `qconf.csv` using `pandas`. Merge or map the configuration limits to the metric time-series.
3. Compute the normalized USE columns.
4. Emit the `quse.csv` file.
5. In `plot-use`, ingest `quse.csv` and use `matplotlib.pyplot` to generate a vertically stacked subplot (3 rows: U, S, E) sharing the X-axis (`time-step`).
6. Save the figure to the designated `--out` path.

## Resources

* Lab PDF: *Queue Lab* §C (USE metric formulas and graphing expectations)
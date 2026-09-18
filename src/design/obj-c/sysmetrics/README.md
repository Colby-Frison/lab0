# System Metrics: Derive and Plot

## Goal

Given the event log (`events.log`) produced by the simulator, derive aggregated, time-series performance metrics (average, median, 10th/90th percentile response times, and throughput) and output them to a structured summary file (`sysmetrics.csv`). Then, generate a visualization (`resplot.png`) to analyze response time variance and system throughput over time.

## CLI sketch

All parameters are command-line arguments (required + optional), allowing these to be run as sequential pipeline steps:

```bash
# 1. Derive the system metrics
derive-sysmetrics \
  --events events.log \
  [--out sysmetrics.csv]      # default: stdout or sysmetrics.csv

# 2. Generate the visual
plot-derive-sysmetrics \
  --sysmetrics sysmetrics.csv \
  [--out resplot.png]         # default: resplot.png

```

## System Metric Definitions

System metrics map the lifecycle of individual jobs using the specific event tokens emitted in the log, and then aggregate those lifecycles at their departure time step.

| Metric | Derivation from `events.log` | Intended insight |
| --- | --- | --- |
| **time-step** | The clock tick when metrics are aggregated. | The x-axis for timeline analysis |
| **Avg-response-time** | The mean of `DEPART-VIA`− `ARRIVE-VIA` for jobs departing in this step| The general turnaround time trend for the system |
| **median-response-time** | The 50th percentile response time for jobs departing in this step | A typical user's experience, resistant to extreme outliers |
| **10-response-time** | The 10th percentile response time | The baseline performance for the fastest/luckiest jobs |
| **90-response-time** | The 90th percentile response time | The long-tail performance, indicating worst-case delays |
| **throughput** | The count of `DEPART-VIA` events in this time step/window | The rate at which the system completes work |

## Worked example (tiny)

Input `events.log`:

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
5 j1 IN q0 ARRIVE-VIA in0.wl
6 j2 IN q0 ARRIVE-VIA in0.wl
10 j0 IN q0 DEPART-VIA out0.wl
15 j1 IN q0 DEPART-VIA out0.wl
15 j2 IN q0 DEPART-VIA out0.wl

```

Possible `sysmetrics.csv` output (using discrete time-step grouping):

```csv
time-step,Avg-response-time,median-response-time,10-response-time,90-response-time,throughput
10,10.0,10.0,10.0,10.0,1
15,9.5,9.5,9.1,9.9,2

```

*(Note: At t=15, j1 had a response time of 10, and j2 had a response time of 9).*

## Implementation plan

1. Parse CLI parameters for both scripts.
2. In `derive-sysmetrics`, parse `events.log` line-by-line to extract the `ARRIVE-VIA` and `DEPART-VIA` timestamps for each job.
3. Calculate the raw response time (departure - arrival) for every job.
4. Group the completed jobs by their `DEPART-VIA` time-step.
5. For each group, use `numpy`/`pandas` to calculate the `mean`, `median`, `quantile(0.10)`, `quantile(0.90)`, and the `size` (throughput).
6. Emit the aggregated data to `sysmetrics.csv`.
7. In `plot-derive-sysmetrics`, ingest `sysmetrics.csv` using `pandas`.
8. Use `matplotlib.pyplot` to generate a dual-axis visualization.
* **Primary Y-Axis:** Plot `Avg-response-time` and `median-response-time` as solid lines. Use `fill_between` with `10-response-time` and `90-response-time` to create a shaded confidence band showing variance.
* **Secondary Y-Axis:** Plot `throughput` as a bar chart or a dashed line in the background to correlate high volume with latency spikes.
9. Save the figure to the designated `--out` path.
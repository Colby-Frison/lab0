# plot-sys-metrics

CLI that plots the CSV written by `derive-sys-metrics` (PDF §C, "Plot System Metrics").

Design notes: [`src/design/obj-c/sysmetrics/README.md`](../../../design/obj-c/sysmetrics/README.md)

## Usage

```bash
python plot_sys_metrics.py --sysmetrics sysmetrics.csv [--out resplot.png]
                           [--title TEXT] [--xlim A:B] [--ylim A:B] [--no-band]
```

| Flag | Meaning |
|------|---------|
| `--sysmetrics` | CSV from `derive-sys-metrics` (required) |
| `--out` | Output PNG (default `resplot.png`) |
| `--title` | Figure title |
| `--xlim A:B` | Time-step limits for both panels |
| `--ylim A:B` | Response-time limits for the latency panel |
| `--no-band` | Hide the shaded P10–P90 band |

Requires `pandas` and `matplotlib`.

## What the figure shows

Two panels sharing the time axis:

1. **Response time (latency) vs time-step** — median (blue) and average (orange)
   response time of the jobs that left the simulator at each step, with a shaded band
   from the 10th to the 90th percentile. A wide band means jobs leaving at the same
   time had very different experiences; average pulling away from median means a long
   tail.
2. **Throughput vs time-step** — how many jobs left per step (or per window).

Read them together: rising latency with flat throughput means the system is
saturated (work is queueing, not completing faster). This is the "response time +
throughput" half of the dashboard; the USE plots from `plot-use` are the other half.

When the CSV was produced with `--dense`, windows with no departures have empty
percentiles and appear as gaps in the latency lines and zeros in throughput. Point
markers are drawn only for short series (≤ 60 rows) so long runs stay readable.

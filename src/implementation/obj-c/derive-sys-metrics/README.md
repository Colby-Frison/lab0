# derive-sys-metrics

CLI that turns the simulator's event log into a time series of **system-level**
response time and throughput (PDF §C, "Derived System Metrics").

Design notes: [`src/design/obj-c/sysmetrics/README.md`](../../../design/obj-c/sysmetrics/README.md)

## Usage

```bash
python derive_sys_metrics.py --events events.log [--out sysmetrics.csv]
                             [--window W] [--dense] [--verbose]
```

| Flag | Meaning |
|------|---------|
| `--events` | Event log written by `simple-queue-sim` / `multi-queue-sim` (required) |
| `--out` | Output CSV; default `-` writes to stdout |
| `--window W` | Group departures into windows of `W` time steps (default `1` = per step). Useful when per-step throughput is 0/1/2 and you want a readable trend |
| `--dense` | Emit a row for every window from 0 to the last event; windows with no departures get `throughput=0` and empty percentiles |
| `-v` | Print counts (queues, arrivals, departures, rows) to stderr |

Requires `numpy`.

## Output

```csv
time-step,Avg-response-time,median-response-time,10-response-time,90-response-time,throughput
```

| Column | Definition |
|--------|------------|
| `time-step` | Time step (or window start) at which the jobs left the simulator |
| `Avg-response-time` | Mean of `DEPART-VIA <sink>` − `ARRIVE-VIA <source>` for jobs leaving in this step |
| `median-response-time` | 50th percentile of the same |
| `10-response-time` | 10th percentile (fastest jobs) |
| `90-response-time` | 90th percentile (long tail) |
| `throughput` | Number of jobs that left the simulator in this step / window |

Response time here is **end-to-end** (source arrival → sink departure). Per-queue
waiting and service times come from `derive-event-metrics`.

### Sources and sinks vs internal edges

The tool first scans the log for every `IN <qsid>` token. An `ARRIVE-VIA x` counts as
a system entry only when `x` is *not* a queue id (it is a source workload such as
`in0.wl`); a `DEPART-VIA x` counts as a system exit only when `x` is not a queue id
(a sink such as `out1.wl`). Hops such as `DEPART-VIA q1` / `ARRIVE-VIA q0` are
internal and ignored. This works for any number of sources and sinks.

Arrivals and departures are paired per job id in FIFO order, so duplicate ids from
several source files still pair sensibly. Jobs that were dropped (`QUEUE-FULL`) or
were still in the system when the run ended never reach a sink; they are reported on
stderr and excluded.

## Worked example

Input:

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
5 j1 IN q0 ARRIVE-VIA in0.wl
6 j2 IN q0 ARRIVE-VIA in0.wl
10 j0 IN q0 DEPART-VIA out0.wl
15 j1 IN q0 DEPART-VIA out0.wl
15 j2 IN q0 DEPART-VIA out0.wl
```

`python derive_sys_metrics.py --events tiny.log`:

```csv
time-step,Avg-response-time,median-response-time,10-response-time,90-response-time,throughput
10,10.00,10.00,10.00,10.00,1
15,9.50,9.50,9.10,9.90,2
```

At t=15 the two response times are 10 and 9; percentiles use linear interpolation
(`numpy.percentile` default), so P10 = 9.1 and P90 = 9.9.

## Pipeline

```bash
python derive_sys_metrics.py --events runs/events.log --out runs/sysmetrics.csv --window 10 --dense
python ../plot-sys-metrics/plot_sys_metrics.py --sysmetrics runs/sysmetrics.csv --out runs/resplot.png
```

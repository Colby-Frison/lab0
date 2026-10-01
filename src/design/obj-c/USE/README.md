# USE Metrics: Compute and Plot

Given `qmet.csv` and the queue config, write `quse.csv`: utilization, saturation, and errors for each queue over sliding windows of 10, 100, and 1000 steps. `plot-use` draws those three series.

This is post-processing. The simulator already recorded the per-step counts.

## CLI

```bash
python compute_use.py --qmet qmet.csv --config qconf.csv [--out quse.csv]
python plot_use.py --quse quse.csv [--qid 0[,1,...]] [--out use.png] [--title TEXT] [--xlim A:B]
```

`--config` supplies `Num. Servers`. Utilization divides busy servers by that count. `q0` in the config and `0` in `qmet.csv` are the same queue.

## Definitions

[Gregg's USE method](https://www.brendangregg.com/usemethod.html) is the resource check (utilization, saturation, errors). The formulas below are the queue slide applied to `qmet.csv`.

| Metric | Window of size $W$ | Unit |
|--------|--------------------|------|
| Utilization | Mean of `num-jobs-in-service / Num. Servers` | fraction in $[0, 1]$ when no more jobs are in service than there are servers |
| Saturation | Mean of `num-jobs-in-queue` | jobs waiting, not a fraction of queue capacity |
| Errors | Sum of `num-of-errors` | jobs dropped in the window |

Each queue is its own history. A window shorter than $W$ uses only the steps that exist. Queues never share a window.

The [Slimmon post](https://blog.danslimmon.com/2019/03/25/latency-and-throughput-optimized-clusters-under-load/) is why these plots sit next to response time and throughput. Those two series stay in `derive-sys-metrics` / `plot-sys-metrics`.

## Worked example

One server. Three steps, so the 10, 100, and 1000 windows are identical.

```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,0,0,0
1,0,2,1,0
2,0,1,1,1
```

```csv
time-step,queue-sys-id,Utilization(10),Saturation(10),Errors(10),Utilization(100),Saturation(100),Errors(100),Utilization(1000),Saturation(1000),Errors(1000)
0,0,0.0,0.0,0,0.0,0.0,0,0.0,0.0,0
1,0,0.5,1.0,0,0.5,1.0,0,0.5,1.0,0
2,0,0.666667,1.0,1,0.666667,1.0,1,0.666667,1.0,1
```

At step 2 the utilization window is $(0 + 1 + 1) / 3$, the saturation window is $(0 + 2 + 1) / 3$, and the error window is $0 + 0 + 1$.

# Multi-queue studio

Prompted session that collects a distribution and the queue settings, writes `in0.wl` and `qconf.csv` through [make-queue-inputs](../make-queue-inputs/README.md), and can run `multi-queue-sim` on those files. It does not add flags of its own. Empty input keeps the value in brackets.

```text
python queue_studio.py
```

From `multi-queue-sim/`:

```text
python tooling/queue-studio/queue_studio.py
```

Defaults match the lab sample: `Sub-10`, rate $10$, two queues, interval `0:9`, seed $42$, one server, waiting max $16$, fixed tasks with work $20$. The default output directory is `multi-queue-sim/runs/studio`. Generation overwrites `in0.wl` and `qconf.csv` in that directory. Choosing not to run leaves any older `qmet.csv`, `events.log`, and `out_final.wl` in place.

## Session

1. Distribution: `fixed`, `uniform`, `normal`, `geometric`, or `poisson`.
2. Interval, seed, and task mode (`fixed` or `dist`), then queue count, waiting max, servers, `Sub-X`, rate, and output directory.
3. Only the statistics that apply come next. `fixed` asks for jobs per time step. `uniform` asks for low and high. `normal` asks for mean and stddev. `geometric` asks for $p$. `poisson` asks for lambda. Task mode `fixed` then asks for tasks per job and work per task. Task mode `dist` skips those two.
4. Confirm generation. `n` exits without writing files.
5. Confirm a simulation run. `y` builds `multi-queue-sim` if `build/` has no binary, then runs `--config`, `--qmet`, and `--events` in the output directory.
6. Optional metric menu.

Ctrl+C or end of input leaves with status $130$.

### Example

Answers below accept every default except the interval and the metric menu.

```text
Multi-queue studio
Press Enter to keep the bracketed default.

  Distribution (fixed/uniform/normal/geometric/poisson) [fixed]:
  Time interval START:END [0:9]: 0:1
  Random seed [42]:
  Task mode (fixed/dist) [fixed]:
  Number of queues [2]:
  Waiting-queue max size [16]:
  Servers per queue [1]:
  Sub-X amount [10]:
  Function rate (ticks between applications) [10]:
  Output directory [.../runs/studio]:
  Jobs per time step [1]:
  Tasks per job [1]:
  Work per task [20]:
  Generate workload and config now? (y/n) [y]:
  Run the generated queue now? (y/n) [y]: n
  Open the metric menu? (y/n) [n]: y
```

## Metric menu

[metrics.py](metrics.py) is a catalog, not an analysis implementation. Choosing a number prints the tool's purpose, the artifact it will read, the future source path, and which of the current run's files already exist. Enter returns to the shell. None of the entries transform data.

| # | Objective | Name | Will read |
|---|-----------|------|-----------|
| 1 | Obj C | filter-by-queue | qmet |
| 2 | Obj C | filter-by-job | events |
| 3 | Obj C | compute-use | qmet |
| 4 | Obj C | plot-use | quse csv |
| 5 | Obj C | derive-sys-metrics | qmet |
| 6 | Obj C | plot-sys-metrics | sysmetrics csv |
| 7 | Obj C | derive-event-metrics | events |
| 8 | Obj C | plot-event-metrics | emetrics csv |
| 9 | Obj C | create-event-trace | events |
| 10 | Obj E | pretty-print-events | events |
| 11 | Obj E | create-config-from-network | network matrix |

Each row is a `MetricTool` (`objective`, `name`, `future_path`, `consumes`, `purpose`). `run` raises `NotImplementedError` with that text. Plot entries consume the CSV their matching derive step will write, which does not exist until those tools are built.

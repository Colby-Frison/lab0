# Objective E — `multi-queue-sim`

C++ discrete-time multi-queue simulator. The binary is the Objective B engine compiled here. `Simulator` already owns a vector of queue systems, so a network is a config with more than one row. There is no second loop.

Design: [src/design/obj-e/README.md](../../../design/obj-e/README.md)  
Parent index: [../README.md](../README.md)  
Engine sources: [../../obj-b/simple-queue-sim/](../../obj-b/simple-queue-sim/)  
Example config: [src/examples/obj-b/multi-queue-config-ex.csv](../../../examples/obj-b/multi-queue-config-ex.csv)

## Directory

```text
multi-queue-sim/
  CMakeLists.txt
  build/                  multi-queue-sim or multi-queue-sim.exe
  scripts/
    run-queue.ps1 / .sh       generate a chain, then simulate
    gen-viz-sim.ps1 / .sh     generate, plot arrivals, then simulate
    run-existing.ps1 / .sh    simulate a workload you already have
  tooling/
    make-queue-inputs/        flag CLI for in0.wl + qconf.csv
    queue-studio/             prompted session
  runs/                   outputs (gitignored)
    queue/                  run-queue
    pipeline/               gen-viz-sim
    existing/               run-existing
    studio/                 queue-studio default
```

## Build

From this directory:

```bash
cmake -S . -B build
cmake --build build
```

Windows binary: `build/multi-queue-sim.exe`. Linux and macOS: `build/multi-queue-sim`. The scripts build it if it is missing.

## CLI

Source, sink, and edges come from the config, not from extra flags.

```text
multi-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events events.log
```

| Flag | Required | Meaning |
|------|----------|---------|
| `--config` | yes | Nine-column `qconf.csv`. One row per queue system. |
| `--qmet` | yes | Dense metrics CSV written by the run. |
| `--events` | yes | Shared event log. |
| `--limit` | no | Stop after this many ticks even if work remains. |

Checked-in `qconf.csv` and `in0.wl` in this directory are a two-queue smoke case: `q0` applies `Sub-10` once and forwards to `q1`, which finishes with `Sub-10*` into `out1.wl`. Expect `DEPART-VIA q1` at time $10$ and `ARRIVE-VIA q0` at time $11$ when the source job has $20$ work.

Each row is one system. Edges such as `[q1,q2]` or `[q1:2.0,q2]` are outgoing routes. A departure at time $t$ is admitted at the peer at $t+1$. `qmet.csv` has one row per $(time, queue-sys-id)$.

## Outputs

| File | Schema |
|------|--------|
| `qmet.csv` | `time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors` |
| `events.log` | `<time> <job-id> IN <qsid> <EVENT> ...` |
| sink `.wl` | Same columns as an Obj A workload. Arrival column is the departure time. `Tasks` is `[]` when the job is done. |

Event names in the log are the file's base name (`out_final.wl`, `q1`), not the absolute path. The simulator still opens the full path from the config.

Which sink name you get depends on the helper:

| Entry | Sink file |
|-------|-----------|
| `make-queue-inputs`, `run-queue`, queue studio | `out_final.wl` |
| `gen-viz-sim`, `run-existing` | `out1.wl` |

## Scripts

Run the PowerShell scripts from this directory. Each has a `.sh` twin for Git Bash or WSL. Passing a `.sh` path to Windows PowerShell opens the file in an editor; it does not execute it.

### `run-queue`

Calls [tooling/make-queue-inputs](tooling/make-queue-inputs/) to write `in0.wl` and `qconf.csv`, then runs the simulator. Default output directory is `runs/queue/`. Unspecified service settings stay at the maker defaults: waiting max $16$, $1$ server, `Sub-10`, rate $10$.

```powershell
.\scripts\run-queue.ps1
.\scripts\run-queue.ps1 -Queues 3 -Interval 0:9 -Dist fixed -FixedWork 20
```

```bash
./scripts/run-queue.sh
QUEUES=3 INTERVAL=0:9 DIST=fixed FIXED_WORK=20 ./scripts/run-queue.sh
```

| PowerShell | Bash env | Default |
|------------|----------|---------|
| `-OutDir` | `OUT_DIR` | `runs/queue` |
| `-Queues` | `QUEUES` | `2` |
| `-Interval` | `INTERVAL` | `0:9` |
| `-Dist` | `DIST` | `fixed` (`fixed`, `uniform`, `normal`, `geometric`, `poisson`) |
| `-Seed` | `SEED` | `42` |
| `-FixedWork` | `FIXED_WORK` | `20` |
| `-FixedTasks` | `FIXED_TASKS` | `1` |
| `-FixedJobs` | `FIXED_JOBS` | `1` |
| `-Lam` | `LAM` | `1.5` (used when `-Dist poisson`) |

### `gen-viz-sim`

Three steps into `runs/pipeline/`: generate a workload with the Obj A generator, write arrival histogram `hist_arrival.png` and scatter `scat_arrival_tasks.png` with the Obj A visualizer, then simulate a fixed two-queue hop. `q0` applies one `Sub-10` and forwards to `q1`, which drains with `Sub-10*` into `out1.wl`. Waiting capacities in this script are $16$ on `q0` and $8$ on `q1`. Distribution extras other than Poisson's `-Lam` are fixed inside the script (`low`/`high` $1$/$3$, normal mean $2$ and stddev $1$, geometric $p=0.4$, one job per step when the distribution is `fixed`).

```powershell
.\scripts\gen-viz-sim.ps1
.\scripts\gen-viz-sim.ps1 -Interval 0:9 -Dist fixed -FixedWork 20 -Seed 1
```

```bash
./scripts/gen-viz-sim.sh
INTERVAL=0:9 DIST=fixed SEED=42 FIXED_TASKS=1 FIXED_WORK=20 ./scripts/gen-viz-sim.sh
```

| PowerShell | Bash env | Default |
|------------|----------|---------|
| `-Interval` | `INTERVAL` | `0:9` |
| `-Dist` | `DIST` | `fixed` |
| `-Lam` | `LAM` | `1.5` |
| `-Seed` | `SEED` | `42` |
| `-TaskMode` | `TASK_MODE` | `fixed` |
| `-FixedTasks` | `FIXED_TASKS` | `1` |
| `-FixedWork` | `FIXED_WORK` | `20` |
| `-OutDir` | `OUT_DIR` | `runs/pipeline` |

### `run-existing`

Does not generate jobs. It points `q0` at a workload you already have, forwards to `q1` (`Sub-10` once, then `Sub-10*`), and writes `out1.wl`, `qmet.csv`, and `events.log` under `runs/existing/`.

```powershell
.\scripts\run-existing.ps1
.\scripts\run-existing.ps1 -Workload ..\..\..\examples\obj-a\wl-poisson.csv
```

```bash
./scripts/run-existing.sh
./scripts/run-existing.sh path/to/workload.csv path/to/out-dir
```

Default workload: [src/examples/obj-a/wl-uniform.csv](../../../examples/obj-a/wl-uniform.csv).

## Tooling

- [make-queue-inputs](tooling/make-queue-inputs/README.md) writes files and stops.
- [queue-studio](tooling/queue-studio/README.md) asks for the distribution and the parameters that distribution uses, then offers to run the sim. The metric menu lists future Obj C and Obj E tools and reports that they are not implemented.

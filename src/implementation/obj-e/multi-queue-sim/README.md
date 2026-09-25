# Objective E — `multi-queue-sim`

C++ discrete-time **multi-queue** simulator.

This binary is the Obj B engine (`simple-queue-sim`) built under the Obj E path.
`Simulator` already owns a vector of queue systems, stages transfers at $t+1$,
and routes on weighted edges. A multi-queue run is a config with more than one
row. There is no second simulation loop.

Design notes: [`src/design/obj-e/README.md`](../../../design/obj-e/README.md)  
Engine: [`../../obj-b/simple-queue-sim/`](../../obj-b/simple-queue-sim/)  
Example multi-row config: [`src/examples/obj-b/multi-queue-config-ex.csv`](../../../examples/obj-b/multi-queue-config-ex.csv)

## Build

```bash
cd src/implementation/obj-e/multi-queue-sim
cmake -S . -B build
cmake --build build
```

Binary: `build/multi-queue-sim` (`.exe` on Windows).

## CLI

Same flags as the single-queue tool. Source, sink, and edges come from the config:

```text
./multi-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events job.log
```

From this directory, after building:

```text
./build/multi-queue-sim --config qconf.csv --qmet qmet.csv --events events.log
```

`qconf.csv` and `in0.wl` are a two-queue smoke test: `q0` applies `Sub-10` once, then forwards residual work to `q1`, which finishes it with `Sub-10*` into `out1.wl`. Expect `DEPART-VIA q1` at time 10 and `ARRIVE-VIA q0` at time 11.

### Scripts

PowerShell (from `multi-queue-sim/`):

```powershell
.\scripts\run-queue.ps1
.\scripts\run-queue.ps1 -Queues 3 -Interval 0:9 -Dist fixed -FixedWork 20
.\scripts\run-existing.ps1
.\scripts\gen-viz-sim.ps1
```

`run-queue` is the one-step path: it calls `make-queue-inputs` to write `in0.wl` and `qconf.csv`, then runs `multi-queue-sim`. Outputs land in `runs/queue/`.

Bash/WSL: `scripts/run-queue.sh`, `scripts/run-existing.sh`, `scripts/gen-viz-sim.sh`.

Both scripts write a two-queue `qconf.csv`, `qmet.csv`, `events.log`, and `out1.wl` under `runs/`. The generate script also writes `in0.wl` and arrival plots. `q0` applies one `Sub-10` and forwards to `q1`, which drains with `Sub-10*`.

Each config row is one queue system. Edges such as `[q1,q2]` or `[q1:2.0,q2]`
are outgoing routes. A departure at time $t$ is admitted at the peer at $t+1$.
`qmet.csv` has one row per `(time-step, queue-sys-id)`. The event log is shared
and includes `qsid` on every line.

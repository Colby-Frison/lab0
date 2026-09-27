# Objective E — Implementation

This directory is the multi-queue side of the lab. The simulator is the Objective B engine built again under this path. Helpers that write workloads and configs live next to that binary.

Design: [src/design/obj-e/README.md](../../design/obj-e/README.md)  
Single-queue engine: [../obj-b/simple-queue-sim/](../obj-b/simple-queue-sim/)

## Layout

```text
obj-e/
  README.md
  multi-queue-sim/
    CMakeLists.txt          compiles Obj B sources into multi-queue-sim
    scripts/                run-queue, gen-viz-sim, run-existing (.ps1 and .sh)
    tooling/
      make-queue-inputs/    flag CLI: in0.wl + linear qconf.csv
      queue-studio/         prompted session; optional immediate run
    runs/                   script and studio output (gitignored)
```

`CMakeLists.txt` points at `../../obj-b/simple-queue-sim` and compiles those sources. Do not copy the engine.

## Status

| Tool | Path | Status |
|------|------|--------|
| Multi-queue sim | [multi-queue-sim/](multi-queue-sim/) | Builds the Obj B engine. A multi-row `qconf.csv` is a network. |
| Make queue inputs | [tooling/make-queue-inputs/](multi-queue-sim/tooling/make-queue-inputs/) | Writes `in0.wl` and a linear-chain config. |
| Queue studio | [tooling/queue-studio/](multi-queue-sim/tooling/queue-studio/) | Prompts, generates, can run the sim. Metric menu is a stub. |
| Pretty-print events | — | Not started. |
| Config from network | — | Not started. |

## Which entry to use

From `multi-queue-sim/`:

| Goal | Command |
|------|---------|
| Generate a chain and run it | `.\scripts\run-queue.ps1` |
| Answer prompts, then run | `python tooling/queue-studio/queue_studio.py` |
| Only write files | `python tooling/make-queue-inputs/make_queue_inputs.py --out-dir runs/mine --queues 2` |
| Plot arrivals, then simulate a fixed two-queue hop | `.\scripts\gen-viz-sim.ps1` |
| Simulate a workload file that already exists | `.\scripts\run-existing.ps1` |

Bash equivalents are `scripts/run-queue.sh`, `scripts/gen-viz-sim.sh`, and `scripts/run-existing.sh`. On Windows PowerShell, invoke the `.ps1` files. Opening a `.sh` script as `.\file.sh` launches it in an editor instead of running it.

Manual run, after `cmake -S . -B build` and `cmake --build build`:

```text
./build/multi-queue-sim --config qconf.csv --qmet qmet.csv --events events.log
```

Details, flags, and output files are in [multi-queue-sim/README.md](multi-queue-sim/README.md).
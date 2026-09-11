# Objective B — Implementation

C++ discrete-time **simple queue simulator** (lab path: `simple-queue-sim/`).

Design, architecture, tick algorithm, and phased build plan:

- [`src/design/obj-b/README.md`](../../design/obj-b/README.md)
- Pseudocode: [`obj_b.pseudocode`](obj_b.pseudocode) (input-driven; serve → move → admit)

## Status

Design / outline only for this pass. The `simple-queue-sim/` C++ tree is **forthcoming** — do not treat this folder as a complete binary yet.

## Planned layout

```text
simple-queue-sim/
  CMakeLists.txt
  README.md
  src/
    main.cpp
    job.hpp / job.cpp
    server_function.hpp/.cpp
    queue_system.hpp/.cpp
    simulator.hpp/.cpp
    workload_io.hpp/.cpp
    event_log.hpp/.cpp
    metrics_writer.hpp/.cpp
```

## Planned CLI

```text
./simple-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events job.log
```

Runs until sources and in-system work are drained (`--limit` is an optional safety cap).

Source/sink paths come from the config CSV (see `examples/obj-b/simple-queue-config-ex.csv`).

## Architecture note

Implement as `Simulator` + `vector<QueueSystem>` even for one queue so Obj E multi-queue is an extension (more config rows + edge routing), not a rewrite.

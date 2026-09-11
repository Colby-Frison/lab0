# Objective B — Implementation

C++ discrete-time **simple queue simulator**.

- Simulator scaffold: [`simple-queue-sim/`](simple-queue-sim/) (see its README for file responsibilities)
- Design / algorithm: [`src/design/obj-b/README.md`](../../design/obj-b/README.md)
- Pseudocode: [`obj_b.pseudocode`](obj_b.pseudocode) (input-driven; serve → move → admit)

## Status

Boilerplate C++ layout is in place under `simple-queue-sim/`. Logic stubs throw / no-op until implemented.

## Quick build

```bash
cd simple-queue-sim
cmake -S . -B build
cmake --build build
```

## CLI

```text
./simple-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events job.log
```

Source/sink paths come from the config CSV (see `examples/obj-b/simple-queue-config-ex.csv`).

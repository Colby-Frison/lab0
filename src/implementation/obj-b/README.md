# Objective B — Implementation

C++ discrete-time **simple queue simulator**.

- Outline / architecture: [`simple-queue-sim/`](simple-queue-sim/) (flowchart, UML, file responsibilities)
- Design / algorithm: [`src/design/obj-b/README.md`](../../design/obj-b/README.md)
- Pseudocode: [`obj_b.pseudocode`](obj_b.pseudocode) (input-driven; serve → move → fill → admit → fill → record)

## Status

Design and outline only. C++ sources will be added during implementation (not scaffolded yet).

## Planned CLI

```text
./simple-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events job.log
```

Source/sink paths come from the config CSV (see `examples/obj-b/simple-queue-config-ex.csv`).

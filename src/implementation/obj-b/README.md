# Objective B — Implementation

C++ discrete-time **simple queue simulator**.

- Simulator: [`simple-queue-sim/`](simple-queue-sim/)
- Design / algorithm: [`src/design/obj-b/README.md`](../../design/obj-b/README.md)
- Pseudocode: [`obj_b.pseudocode`](obj_b.pseudocode) (input-driven; serve → move → fill → admit → fill → record)

## Status

Working C++ implementation with CMake build and CTest suite (`run-all-tests.sh`).

## Build and test

```bash
cd simple-queue-sim
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
# or: ./run-all-tests.sh
```

## CLI

```text
./simple-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events job.log
```

Source/sink paths come from the config CSV (see `examples/obj-b/simple-queue-config-ex.csv`).

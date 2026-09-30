# Lab 0: Discrete-Time Queueing

CS-41113 / CS 5/4113, Distributed Operating Systems, Fall 2026.

Group 5: Colby Frison, Jhan Paul Mackey, Caleb Furley, Levin Ward, Felix Werner.

This repository is a discrete-time tool-chain for modeling computer and service systems as queues. Python tools synthesize and plot workloads. A C++ simulator advances one global clock and writes queue metrics, an event log, and completed jobs. Analysis tools then derive utilization, saturation, errors, response time, and throughput from those outputs. The same engine runs one station or a network of stations.

This README is the project guide and the statement of work. The graded items come from the course task lists (`Documentation/local-notes/tasks.md` and `Documentation/local-notes/technical_tasks.md`). The course paths in those lists (`./implementation`, `./examples`, `./analysis`, `./designs`, `./lab`) map onto the `src/` tree and `Documentation/` as shown below.

## Statement of work

### Purpose

The lab requires a reproducible way to measure latency, utilization, and loss for a queue before that design is built. Work arrives over discrete time steps, waits in a finite buffer, and is processed by servers that change each job's task list until the job is complete (`Tasks == []`). Closed forms such as $M/M/1$ assume memoryless arrivals and service. The workloads here are bursty, jobs contain several tasks, and the order of work inside one time step changes the recorded events. The tool-chain is the way those systems get measured.

### Scope

In scope:

- A workload generator and visualizer (Objective A).
- A C++ single-queue simulator (Objective B) whose configuration can also describe a network.
- Analysis and plotting tools over the metric file and the event log (Objective C).
- One real system modeled as a single queue, with plots and written answers (Objective D).
- A C++ multi-queue entry point, an event-log pretty printer, and a converter from a network file to a queue configuration (Objective E).
- The same kind of study at three network scales (Objective F): tens of queues, hundreds of queues, and thousands of queues.
- Hand-written examples, design notes and pseudocode, automated tests, a root test runner, GitLab CI, and the technical report and presentation.

A deliverable is complete when the tool runs from the command line on the example inputs, its tests pass where a suite exists, and, for Objectives D and F, the artifacts and the answers to the slide questions sit in the analysis directory named in the table.

### Team

| Name | Role |
| --- | --- |
| Colby Frison | Manager |
| Jhan Paul Mackey | Tech lead |
| Caleb Furley | Member |
| Levin Ward | Member |
| Felix Werner | Member |

### Examples and designs

The task list assigns 10 points to each example family and 10 points to the pseudocode, a worked input and output, and resources for each tool. Those notes live under `src/examples/` and `src/design/`. The paths below are the ones in this repository. The task list uses `./examples` and `./designs` without the `src/` prefix.

## Layout

```text
lab0/
  README.md                 this statement of work and usage guide
  run-all-tests.sh          course runner (placeholder)
  src/
    design/                 pseudocode and design notes, one folder per objective
    examples/               hand-written samples the tools are checked against
    implementation/         programs, one folder per objective and one per tool
    analysis/
      ObjD/                 single-queue study (empty)
      ObjF/                 scale index
      multi-SMALL/          emergency-department study
  Documentation/
    Resources/              course slides (Queue Lab.pdf)
    local-notes/            task lists and the report draft (gitignored)
```

Each objective has its own folder. Each tool has its own subfolder and its own README with flags and output columns.

## Requirements

- A C++17 compiler and CMake, for `simple-queue-sim` and `multi-queue-sim`.
- Python 3. The generator and the per-visit event metrics use the standard library. The visualizer, the queue filter, and the plotting tools need `pandas` and `matplotlib`. Deriving system metrics also needs `numpy`.

## Usage

Tool READMEs under `src/implementation/` are the full flag lists. The path below is enough to generate a workload, simulate one queue, and plot response time.

### 1. Workload

From the repository root. `--interval` is inclusive.

```bash
python src/implementation/obj-a/workload-generator/workload_generator.py \
  --interval 0:49 --dist poisson --lam 2 --seed 4113 --out wl.csv

python src/implementation/obj-a/workload-visualizer/workload_visualizer.py wl.csv \
  --hist "arrival time" --bins 20 --out hist.png

python src/implementation/obj-a/workload-visualizer/workload_visualizer.py wl.csv \
  --scat "arrival time,len(Tasks)" --out scat.png
```

Distributions are `fixed`, `uniform`, `normal`, `geometric`, and `poisson`. Task counts and task work follow that distribution unless `--task-mode fixed` is set.

### 2. Single queue

```bash
cd src/implementation/obj-b/simple-queue-sim
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

The binary name depends on the CMake generator (`build/simple-queue-sim` or `build/Debug/simple-queue-sim.exe`).

```text
simple-queue-sim --config qconf.csv [--limit T] --qmet qmet.csv --events events.log
```

Source and sink filenames come from the configuration, as in `src/examples/obj-b/simple-queue-config-ex.csv`. One clock step is serve, move, fill, admit, fill, record. The process stops when every source is exhausted and no job is waiting, in service, or in a transfer buffer. `--limit` is an optional cap.

On Windows, `.\scripts\gen-viz-sim.ps1` generates a workload, plots it, and runs the simulator. `.\scripts\run-existing.ps1` simulates a workload file that already exists. Bash equivalents are the `.sh` scripts in the same folder.

### 3. Analysis

From `src/implementation/obj-c`, pointed at a simulator run:

```bash
python derive-sys-metrics/derive_sys_metrics.py --events events.log --out sysmetrics.csv --window 10
python plot-sys-metrics/plot_sys_metrics.py --sysmetrics sysmetrics.csv --out resplot.png
python derive-event-metrics/derive_event_metrics.py --events events.log --out emetrics.csv
python filter-by-queue/filter_by_queue.py --qmet qmet.csv --qid 0 --out q0.csv
python create-event-trace/create_event_trace.py --events events.log --out etrace.png
```

```bash
python -m unittest discover -s tests -v
```

### 4. A network of queues

`src/implementation/obj-e/multi-queue-sim` compiles the same sources. A multi-row configuration is the network. Build it the same way as the single-queue simulator.

```text
multi-queue-sim --config qconf.csv --qmet qmet.csv --events events.log
```

Helpers next to that binary:

```bash
python src/implementation/obj-e/multi-queue-sim/tooling/make-queue-inputs/make_queue_inputs.py \
  --out-dir runs/mine --queues 2

python src/implementation/obj-e/create-config-network/create_config_from_network.py \
  --network src/examples/obj-e/network-dummy.mtx --out qconf.csv

python src/implementation/obj-e/pretty-print-events/pretty_print_events.py events.log
```

`queue_studio.py` asks for a distribution and queue settings, writes the inputs, and can run the simulator.

### 5. Tests per objective

| Suite | Command |
| --- | --- |
| Objective B | `src/implementation/obj-b/simple-queue-sim/run-all-tests.sh` or `run-all-tests.ps1` |
| Objective C | `src/implementation/obj-c/run-all-tests.sh` or `run-all-tests.ps1` |
| Objective E | `src/implementation/obj-e/run-all-tests.sh` or `run-all-tests.ps1` |

On Windows, use the PowerShell scripts. A `.sh` file opened from PowerShell is edited, not executed.

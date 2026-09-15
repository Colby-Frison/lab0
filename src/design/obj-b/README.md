# Objective B — Design: Simple Queue Simulator

## Premise

Objective B builds the discrete-time **queueing simulator** that consumes Obj A workloads and produces metrics/logs for Obj C analysis tools.

Deliverable (from `tasks.md` / Queue Lab slides):

| Tool | Path | Role |
|------|------|------|
| Simple queue sim | `implementation/obj-b/simple-queue-sim/` | C++ CLI: config + source wl → sink wl, `qmet.csv`, event log |

**Language: C++** (required).

### Resource map

| Resource | Use |
|----------|-----|
| [Queue Lab.pdf](../../../Documentation/Resources/Queue Lab.pdf) §B (pp. 6–14) | Queue system model, config schema, server functions, qmet, events |
| Queue Lab.pdf p. 15 | Reference tick sketch (our loop is input-driven; see Main loop below) |
| [q_ex-1.py](../../../Documentation/Resources/example/q_ex-1.py) | Teaching toy for discrete-time intuition (fixed service time — **not** our job model) |
| [server-func.cpp](../../examples/obj-b/server-func.cpp) | `Sub-X` / chain examples on task lists |
| [simple-queue-config-ex.csv](../../examples/obj-b/simple-queue-config-ex.csv) | Single-node Obj B config |
| [multi-queue-config-ex.csv](../../examples/obj-b/multi-queue-config-ex.csv) | Same schema, N nodes (Obj E foreshadow) |
| [events-single.csv](../../examples/obj-b/events-single.csv), [qmet-single.csv](../../examples/obj-b/qmet-single.csv) | Expected event/metric shapes |
| Obj A workload CSV | Source/sink file format |

### Non-goals for this design pass

- No full C++ simulator implementation yet
- No Obj E MTX network loader / pretty-printer
- Do not hard-code “exactly one queue forever” — Obj B is a **network of size 1**

---

## Shared job / workload format (from Obj A)

| Column | Meaning |
|--------|---------|
| `Job Id` | Stable id (`j0`, `j1`, …) |
| `arrival time` | Enter time (source) **or** leave time (sink / completed) |
| `Tasks` | Ordered `"<tid>: W N"` strings; `[]` means done |

Source example (work remaining):

```csv
Job Id,arrival time,Tasks
j0,0,"[""0: W 10"", ""1: W 10""]"
j1,10,"[""0: W 10""]"
j2,20,"[""0: W 10"", ""1: W 10"", ""2: W 10""]"
```

Sink example (completed; `arrival time` = departure time):

```csv
Job Id,arrival time,Tasks
j0,20,[]
j1,30,[]
```

---

## Queue system model (PDF §B)

Each **Queue System** has:

- Waiting queue with **max size**
- **N servers**
- **Server function** + **rate** (apply function once every `rate` time steps while a job is in service)
- Optional **source** workload file (incoming edge from outside)
- Optional **sink** workload file (outgoing edge to outside)
- **Edges in** / **Edges out** to other queue systems (empty for Obj B single-node)

```mermaid
flowchart LR
  source["source .wl"] --> qs
  edgesIn["Edges in"] --> qs

  subgraph qs ["Queue System"]
    direction TB
    waiting["Waiting queue max size"] --> servers["Servers x N"]
    servers --- fnRate["fn + rate"]
  end

  qs --> sink["sink .wl"]
  qs --> edgesOut["Edges out"]
  qs --> logs["qmet.csv + event log"]
```

### Config schema

Columns (see examples):

```text
Sys ID, Queue Max Size, Num. Servers, Server Function, Server Function Rate, Source, Sink, Edges in, Edges out
```

Obj B single node:

```csv
Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
q0,8,1,Sub-10,10,in0.wl,out0.wl,[],[]
```

Multi-queue (same loader later):

```csv
q0,16,3,Sub-10,10,in0.wl,,[],[q1,q2]
q1,8,1,Sub-5,5,,out1.wl,[q0],[]
q2,10,4,Sub-10,10,,out2.wl,[q0],[]
```

Architecture rule: parse **all rows** into a `vector<QueueSystem>`. Obj B configs simply have one row and empty edges.

---

## Server functions (PDF pp. 8–9)

A server function takes a task list and returns a mutated task list after each **rate** window.

**Sub-X:** subtract `X` from the first task’s `W N`, or remove the first task if `N <= X`.

| Task-In | Sub-10 → Task-Out |
|---------|-------------------|
| `["0: W 10"]` | `[]` |
| `["0: W 20"]` | `["0: W 10"]` |
| `["0: W 10", "1: W 10"]` | `["1: W 10"]` |
| `[]` | `[]` |

**Chains** (e.g. `Sub-5,Sub-10`): apply each function over successive rate windows (Sub-5 for `rate` steps, then Sub-10 for `rate` steps, …). Reference: `examples/obj-b/server-func.cpp`.

PDF sample assumes **Sub-10\*** — Sub-10 applied 0 or more times until tasks are complete before the job leaves (Obj B single-queue assumption; not always true in multi-queue).

---

## Architecture (multi-queue-ready)

Build Obj B as a **network of size 1**, not a hard-coded single queue class.

```mermaid
flowchart LR
  config["Queue config CSV"] --> sim["Simulator"]
  sources["Sorted source workloads"] --> sim
  sim --> systems["QueueSystem collection"]
  systems --> sinks["Per-queue sink workloads"]
  systems --> transfers["Staged inter-queue transfers"]
  transfers --> systems
  sim --> qmet["Shared qmet.csv"]
  sim --> events["Shared event log"]
```

Later Obj E adds more `QueueSystem` nodes and routes `DEPART` along edges (equal weight if unspecified) instead of only to a sink.

### Core C++ types

| Type | Responsibility |
|------|----------------|
| `Job` | id, original source arrival, current-queue arrival, task list |
| Task helpers | parse/format `"tid: W N"` |
| `ServicePlan` / `ServerFunction` | ordered functions, `*` repeat policy, and pure `SubX` task mutation |
| `Server` | optional job, rate timer, function index, service-visit-complete state |
| `Transfer` | job, source/target queue ids, and the time it becomes admissible |
| `QueueSystem` | id, max size, FCFS waiting deque, servers, service plan, source/sink, weighted edges, current/next transfer buffers, per-step errors |
| `Simulator` | load config → systems; global clock; tick loop; orchestrate routing |
| `SourceStream` / `SinkWriter` | one-row-lookahead source reads and persistent sink writes using Obj A CSV |
| `EventLog` / `MetricsWriter` | event lines + qmet rows |

**Key rule:** all “how a queue works” logic lives in `QueueSystem` + the PDF tick order in `Simulator`. Obj E should extend routing and config size, not fork a second simulator.

---

## Main loop (input-driven; one complete pass per clock)

Loop while **work remains** (source jobs, waiting jobs, busy servers, or staged
transfers), with `--limit` only as a safety guard. Each clock value is handled
exactly once. This avoids the previous two-branch design, which could admit a
new job before recording a same-time service completion.

The canonical order is:

1. **Serve** jobs already in service for one unit of simulated time.
2. **Move** every completed service visit: a done job goes to its sink when
   present; otherwise any visit-complete job follows a staged outgoing edge.
   No valid destination is an error.
3. **Fill** idle servers from the existing FCFS waiting queues.
4. **Admit** all source arrivals and transfers available at this time. After
   older waiting jobs have been dispatched, a new job uses any remaining idle
   server; otherwise it joins the waiting tail or is rejected with
   `QUEUE-FULL`.
5. **Fill again** so a new arrival can start immediately.
6. **Record** one qmet row per queue, commit transfers for the next time, and
   increment the clock.

```text
clock = 0
systems = load_config()   # one QS for Obj B; many for Obj E

while work_remaining(systems):          # <-- main loop
  if --limit hit: break

  reset per-step errors
  serve all busy servers
  move every service-visit-complete job
    if Tasks == [] and sink exists: write sink
    else if edges_out exists: stage transfer for clock + 1
    else: ERROR NO-OUT-EDGE
  fill idle servers from existing waiting jobs
  admit every source job and available transfer due at clock
  fill idle servers again
  write qmet row for every queue
  commit next-step transfers
  clock++
```

See `implementation/obj-b/simple-queue-sim/README.md` for the full flowchart
plus efficiency (dense time, safe idle jumps, deques, maps) and queueing-theory
(FCFS, work-conserving, Little's Law, utilization, loss buffers) notes.

### Timing invariants

- Existing service events precede arrivals with the same timestamp.
- Transfers departing at $t$ become available to the target at $t+1$, so
  results do not depend on queue iteration order.
- Queue capacity counts waiting jobs only; in-service jobs are separate.
- qmet errors are per-step dropped jobs and reset after emission.
- One dense qmet row per `(time-step, queue-sys-id)` is required for Obj C's
  10/100/1000-step USE windows.
- Service-visit completion is distinct from job completion (`Tasks == []`).
  `Sub-10*` repeats until done; a non-repeating stage can forward remaining
  work to another queue.

### Efficiency and analysis constraints

- Use deques for O(1) FCFS admission/dispatch and a queue-id hash map for O(1)
  routing.
- Never rescan a source workload; consume its sorted front cursor.
- Dense qmet imposes an unavoidable $\Omega(QT)$ output cost. A clock jump is
  safe only across a fully idle gap and must still synthesize required qmet
  rows.
- Preserve original and per-queue arrival times so Obj C can derive queue
  response/turnaround and system latency/throughput.
- Sections D/F require comparable sensitivity studies. Weighted routing must
  therefore be deterministic (weighted round-robin) or explicitly seeded.
- For stable intervals, validate measurements with Little's Law
  $L \approx \lambda W$; report warm-up and drain intervals separately from
  steady state.

### Multi-queue I/O and logging

| Concern | How |
|---------|-----|
| Input | Per-QS sorted `SourceStream` with one-row lookahead; plus staged transfers from upstream DEPART |
| Output | Persistent per-QS `SinkWriter` (empty `Tasks`, departure time in arrival column) |
| Events | **One** shared event log; every line includes `qsid` so filters work across the network |
| Metrics | **One** `qmet.csv`; one row per `(clock, queue-sys-id)` for all systems |

Obj B is just `systems.size() == 1` with empty edges; Obj E reuses the same loop.

### Contrast with `q_ex-1.py` / PDF p. 15

- `q_ex-1.py`: fixed `service_time`, single queue, `while clock < limit`
- PDF p. 15 sketch: for-each-QS phases under a time limit (move → update → fill → admit)
- **Our outline:** input-driven stop; **serve → move → admit**; task-list mutation via server functions; N queue systems from day one

### Pseudocode files

- [`simple-queue-sim/simple-queue-sim.pseudo`](simple-queue-sim/simple-queue-sim.pseudo)
- [`../../implementation/obj-b/obj_b.pseudocode`](../../implementation/obj-b/obj_b.pseudocode)

---

## Outputs

### Queue metrics (`qmet.csv`)

Every time step × every queue system:

```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
...
5,0,3,1,1
```

- `num-jobs-in-queue` — waiting (saturation / L)
- `num-jobs-in-service` — occupied servers
- `num-of-errors` — jobs dropped by this queue during this time step; reset
  after the row is emitted

### Event log

Tokens from PDF pp. 12–13:

```text
<time> <job-id> IN <qsid> ARRIVE-VIA <edge>
<time> <job-id> IN <qsid> DEPART-VIA <edge>
<time> <job-id> IN <qsid> ENTERS-SERVER <sid>
<time> <job-id> IN <qsid> EXITS-SERVER <sid>
<time> <job-id> IN <qsid> TASK-START <tid> <task>
<time> <job-id> IN <qsid> TASK-END <tid> <task>
<time> <job-id> IN <qsid> ERROR <QUEUE-FULL|NO-OUT-EDGE>
```

Sample (matches `examples/obj-b/events-single.csv` / PDF Sub-10\* walkthrough):

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
0 j0 IN q0 ENTERS-SERVER 0
0 j0 IN q0 TASK-START 0 "W 10"
10 j0 IN q0 TASK-END 0 "W 10"
10 j0 IN q0 TASK-START 1 "W 10"
...
```

---

## Worked single-queue walkthrough (sketch)

Config: `q0`, max 8, 1 server, `Sub-10`, rate 10, source `in0.wl`, sink `out0.wl`, no edges.

Source jobs (PDF-style):

| Job | arrival | Tasks |
|-----|---------|-------|
| j0 | 0 | `["0: W 10", "1: W 10"]` |
| j1 | 10 | `["0: W 10"]` |
| j2 | 20 | `["0: W 10", "1: W 10", "2: W 10"]` |

Expected behavior under Sub-10 every 10 steps:

- t=0: j0 arrives, enters server 0, starts task 0
- t=10: task 0 ends, task 1 starts; j1 arrives and waits
- t=20: j0 finishes tasks, exits server, departs to sink; j1 enters service; j2 arrives
- … continue until sources and in-system work are drained

Validate events against `examples/obj-b/events-single.csv` when implementing.

---

## Implementation outline (C++, forthcoming)

Target: `src/implementation/obj-b/simple-queue-sim/`

```text
simple-queue-sim/
  CMakeLists.txt          # or Makefile
  README.md               # build + run
  src/
    main.cpp              # CLI
    config_io.hpp/.cpp    # qconf CSV + weighted edges
    job.hpp / job.cpp
    server_function.hpp/.cpp   # ServicePlan, Sub-X, chains, * repeat
    queue_system.hpp/.cpp
    simulator.hpp/.cpp
    workload_io.hpp/.cpp       # streaming Obj A sources / persistent sinks
    event_log.hpp/.cpp
    metrics_writer.hpp/.cpp    # qmet.csv
```

### CLI sketch

```text
./simple-queue-sim \
  --config qconf.csv \
  [--limit T] \              # optional safety cap; default: run until drained
  --qmet qmet.csv \
  --events job.log
```

Source/sink paths come from the config columns (relative to cwd), matching examples.

### Phased build (later coding)

1. I/O + Job/Task parse; `Sub-X` unit-testable without the clock
2. One `QueueSystem`, one server, source→sink, empty edges (Obj B MVP)
3. Multi-server in one QS; `QUEUE-FULL`; full event vocabulary + qmet
4. Chained server functions + rate timing
5. Edge buffers + weighted routing (unlocks Obj E without rewrite)

---

## Acceptance checklist (eventual C++ MVP)

- [ ] Loads config CSV; builds ≥1 `QueueSystem` (Obj B: one row)
- [ ] Reads Obj A source workload; writes sink workload with empty `Tasks`
- [ ] Discrete clock; loop until inputs/in-system work drain; serve → move → admit
- [ ] Applies `Sub-X`, chains, and `*` repeat semantics at the configured rate
- [ ] Emits `qmet.csv` and event log matching lab token formats
- [ ] Reports `QUEUE-FULL` when waiting queue cannot accept an arrival
- [ ] Distinguishes service-visit completion from `Tasks == []`
- [ ] Stages inter-queue transfers for deterministic $t+1$ admission
- [ ] Preserves original and per-queue arrival timestamps for Obj C metrics
- [ ] Types/structure leave room for N systems + edges (no single-queue-only dead ends)

---

## How Obj B fits the lab

```mermaid
flowchart TB
  gen["Obj A generator"] --> in0["in0.wl"]
  conf["qconf.csv"] --> sim["Obj B simple-queue-sim"]
  in0 --> sim
  sim --> out0["out0.wl"]
  sim --> qmet["qmet.csv"]
  sim --> joblog["job.log"]
  out0 --> objc["Obj C filters / USE / metrics / traces"]
  qmet --> objc
  joblog --> objc
  sim -.-> obje["Obj E: same engine multi-row config + edges"]
```

# Objective E — Design: Multi-Queue Network

Objective E runs the same discrete-time simulator as Objective B on a config with more than one queue system. There is no second clock and no second simulation loop. A network is a set of rows in `qconf.csv` that route leftover work to each other.

Engine behavior is defined in [Objective B](../obj-b/README.md). This note covers what changes when several systems share one clock, plus the helpers that build those configs.

## Deliverables

| Tool | Path | Role |
|------|------|------|
| Multi-queue sim | `implementation/obj-e/multi-queue-sim/` | C++ binary. Compiles the Obj B engine under the Obj E path. |
| Make queue inputs | `implementation/obj-e/multi-queue-sim/tooling/make-queue-inputs/` | Python CLI. Writes `in0.wl` and a linear-chain `qconf.csv`. |
| Queue studio | `implementation/obj-e/multi-queue-sim/tooling/queue-studio/` | Interactive CLI. Prompts for parameters, calls the maker, optionally runs the sim. |
| Pretty-print events | [implementation/obj-e/pretty-print-events/](../../implementation/obj-e/pretty-print-events/) | Aligned terminal view of `events.log`. Sketch: [pretty-print-event.pseudo](pretty-print-event.pseudo). |
| Config from network | not started | Build `qconf.csv` from a network matrix. [create-config-network.pseudo](create-config-network.pseudo) and [multi-queue-sim.pseudo](multi-queue-sim.pseudo) are empty. |

Language: the simulator is C++17. Generators and the studio are Python. Analysis tools that consume the logs belong to Objective C and are not implemented yet.

## One clock, N systems

Each tick still walks every queue system in one pass: serve, move completed jobs, fill idle servers, admit arrivals, fill again, then record metrics. The stop condition is input-driven: the run ends when sources are exhausted and no queue still holds work. `--limit` is only a safety cap.

Work is conserved the same way as in a single queue. A server applies `Sub-X` to the front task. A visit ends when the service plan finishes. A job is done only when `Tasks` is empty. Sink output happens only if the job is done and that row has a sink. Otherwise the job is offered to an outgoing edge.

## Config schema

One row is one queue system. Header:

```text
Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
```

| Column | Meaning |
|--------|---------|
| Sys ID | `q0`, `q1`, … |
| Queue Max Size | Waiting capacity. A job in service does not occupy a waiting slot. |
| Num. Servers | Parallel servers. An idle server is preferred over dropping a job. |
| Server Function | `Sub-X` applies the plan once. `Sub-X*` repeats until `Tasks` is empty. |
| Server Function Rate | Ticks between applications. The server stays occupied on the ticks in between. |
| Source | Workload path. Usually only the first queue has one. |
| Sink | Completed-job file. Usually only the last queue has one. |
| Edges in | Declared predecessors. Parsed and stored. Admission does not use this column. |
| Edges out | Successors. This is what routing follows. |

Example of two rows: [multi-queue-config-ex.csv](../../examples/obj-b/multi-queue-config-ex.csv).

## Routing

A departure at time $t$ is admitted at the peer at time $t+1$. Staging the handoff one tick later keeps the result independent of the order the systems are visited in that tick.

Outgoing edges are a weighted round-robin. An unweighted target counts as weight $1$. Weights are expanded by $1000$ slots, so equal weights do not alternate one job at a time: the first block of picks stays on the first edge. A list such as `[q1:2.0,q2]` sends about twice as many jobs toward `q1` as toward `q2` over a long run.

A queue may list several outgoing edges and several named incoming edges. The engine supports that fan-in and fan-out. The helper that writes configs does not: `make-queue-inputs` always emits a straight line, `q0` to `q1` to `q2`, with one out-edge each until the last row.

If a job still has tasks, the plan does not repeat, and there is no out-edge, the log records `ERROR NO-OUT-EDGE`. If waiting room and every server are full, the log records `ERROR QUEUE-FULL`.

## Linear chain the helpers build

The tooling chain is a convenience, not a limit of the simulator.

- Queue $0$ reads `in0.wl`, applies `Sub-X` once, and forwards on `[q1]`. Residual work is intentional when task work is larger than `Sub-X`.
- Middle queues have an empty source and an empty sink. They take one hop from the previous id and send one hop to the next.
- The last queue uses `Sub-X*` and writes `out_final.wl`.

Default service in the helpers is `Sub-10` with rate $10$, matching the lab sample (one application of $10$ work units every $10$ ticks). `Sub-1` with rate $1$ has the same average pace when the remaining work is a multiple of $10$. Leftover work smaller than `Sub-X` still waits out a full rate window before the next application.

## Event log and metrics

`qmet.csv` is dense: one row per $(time, queue-sys-id)$.

```text
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
```

The per-tick error count is cleared at the start of each clock, then written into `num-of-errors`.

The event log is one shared file. Every line names the queue:

```text
<time> <job-id> IN <qsid> <EVENT> ...
```

Tokens include `ARRIVE-VIA`, `DEPART-VIA`, `ENTERS-SERVER`, `EXITS-SERVER`, `TASK-START`, `TASK-END`, `ERROR QUEUE-FULL`, and `ERROR NO-OUT-EDGE`. Edge labels in the log use the file name only. The simulator still opens the full source and sink paths.

## Future tools

Pretty-print groups events by time, then by queue, and writes an aligned column per queue. Widths use the visible text so ANSI color codes do not shift the columns. The implementation is [pretty-print-events](../../implementation/obj-e/pretty-print-events/). A terminal session opens the result in `less -R` when that pager is available.

Config-from-network will turn a network description into the same nine-column `qconf.csv`. Until that exists, fan-out configs are written by hand, and linear chains come from the tooling.
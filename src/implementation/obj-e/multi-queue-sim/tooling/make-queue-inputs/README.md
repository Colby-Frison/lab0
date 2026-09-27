# make-queue-inputs

Writes an Objective A workload and a linear multi-queue `qconf.csv`. It does not run the simulator.

The first queue reads `in0.wl`, applies `Sub-X` once, and forwards to the next id. Each middle queue does the same. The last queue uses `Sub-X*` and writes `out_final.wl`. Paths in the config are absolute. Fan-out is not generated here; every non-final row has one out-edge.

[run-queue](../../scripts/run-queue.ps1) calls this utility and then runs `multi-queue-sim`. The generator it shells out to is [workload_generator.py](../../../../../../src/implementation/obj-a/workload-generator/workload_generator.py).

From this directory:

```text
python make_queue_inputs.py --out-dir ..\..\runs\auto --queues 2 --interval 0:9 --dist fixed --fixed-work 20
```

From `multi-queue-sim/`:

```text
python tooling/make-queue-inputs/make_queue_inputs.py --out-dir runs/auto --queues 2 --interval 0:9 --dist fixed --fixed-work 20
```

`--out-dir` is required. `--queues` must be at least $1$. The command prints the workload path and the config path.

## How a chain is written

For queue index $i$ in $0 \ldots N-1$:

| Row | Source | Sink | Edges in | Edges out | Function |
|-----|--------|------|----------|-----------|----------|
| $i = 0$, and it is also last | `in0.wl` | `out_final.wl` | `[]` | `[]` | `Sub-X*` |
| $i = 0$, not last | `in0.wl` | empty | `[]` | `[q1]` | `Sub-X` |
| middle | empty | empty | `[q{i-1}]` | `[q{i+1}]` | `Sub-X` |
| last, $i > 0$ | empty | `out_final.wl` | `[q{i-1}]` | `[]` | `Sub-X*` |

`Edges in` is recorded for readability. The simulator routes on `Edges out`.

Every row gets the same `--max-size`, `--servers`, `--sub`, and `--rate`.

## Flags

Only the statistics for the chosen `--dist` are forwarded to the Obj A generator. The other distribution flags are accepted and ignored for that run. `--fixed-tasks` and `--fixed-work` are forwarded only as generator arguments; the generator applies them when `--task-mode` is `fixed`.

### Topology

| Flag | Default | Effect |
|------|---------|--------|
| `--out-dir` | required | Directory for `in0.wl` and `qconf.csv`. Created if missing. |
| `--queues` | `2` | Number of rows. |
| `--max-size` | `16` | Waiting capacity on every row. |
| `--servers` | `1` | Servers on every row. |
| `--sub` | `10` | `Sub-X` amount. Last row is `Sub-X*`. |
| `--rate` | `10` | Ticks between applications of that function. |

### Workload

| Flag | Default | Effect |
|------|---------|--------|
| `--interval` | `0:9` | Inclusive `START:END` passed to the generator. |
| `--dist` | `fixed` | `fixed`, `uniform`, `normal`, `geometric`, or `poisson`. |
| `--seed` | `42` | Generator seed. |
| `--task-mode` | `fixed` | `fixed` uses `--fixed-tasks` and `--fixed-work`. `dist` draws task counts and work from the same family as arrivals. |

### Used only for the matching distribution

| Flag | Default | Used when |
|------|---------|-----------|
| `--fixed-jobs` | `1` | `--dist fixed` |
| `--low`, `--high` | `1`, `3` | `--dist uniform` |
| `--mu`, `--sigma` | `2.0`, `1.0` | `--dist normal` |
| `--p` | `0.4` | `--dist geometric` |
| `--lam` | `1.5` | `--dist poisson` |
| `--fixed-tasks` | `1` | `--task-mode fixed` |
| `--fixed-work` | `20` | `--task-mode fixed` |

Default work of $20$ with `Sub-10` leaves residual work after the first hop, so the second queue actually receives a job.

## Examples

Two queues, Poisson arrivals, four servers, larger waiting room:

```text
python make_queue_inputs.py --out-dir runs/poisson --queues 2 --interval 0:30 --dist poisson --lam 2.5 --task-mode fixed --fixed-tasks 1 --fixed-work 20 --servers 4 --max-size 32
```

Three hops, one application of $5$ work every $5$ ticks, last hop repeats until the job is done:

```text
python make_queue_inputs.py --out-dir runs/three --queues 3 --sub 5 --rate 5 --fixed-work 15
```

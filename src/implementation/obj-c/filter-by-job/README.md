# filter-by-job

CLI that keeps only the `events.log` lines of one or more jobs (PDF §C,
"Filtering Event Logs"). Use it to follow a single job through the queue network.

Design notes: [`src/design/obj-c/filters/README.md`](../../../design/obj-c/filters/README.md)

## Usage

```bash
./filter_by_job.py --events events.log --jobs 0[,1,...] [--out jobout.log]
```

| Flag | Meaning |
|------|---------|
| `--events` | Event log written by `simple-queue-sim` / `multi-queue-sim` (required) |
| `--jobs` | Job id, or a comma-separated list such as `0,2` (required). `--jobs=0` and `--jobs 0` both work |
| `--out` | Output log; default `-` writes to stdout |

Standard library only; no extra packages needed.

## Job ids

The event log uses the ids from the workload file, e.g. `j0`. `--jobs` accepts either
form: a bare number gets the `j` prefix (`0` → `j0`, `007` → `j7`), and anything else
is used as given (`j0` → `j0`).

## Matching

Every event line has the form `<time> <job-id> IN <qsid> <EVENT> <rest>`. Only the
**second token** is compared, and only as an exact match:

- `j1` does not match `j10`;
- a `j0` elsewhere on a line (e.g. inside the event text) is ignored.

Matching lines are written unchanged and in their original order. If several jobs are
requested, their lines stay interleaved by time. A job that does not occur in the log
gives empty output. Blank lines, and lines too short to have a second token, are
dropped.

## Worked example

Input `events.log`:

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
0 j0 IN q0 ENTERS-SERVER 0
0 j0 IN q0 TASK-START 0 "W 10"
10 j0 IN q0 TASK-END 0 "W 10"
10 j0 IN q0 TASK-START 1 "W 10"
10 j1 IN q0 ARRIVE-VIA in0.wl
20 j0 IN q0 TASK-END 1 "W 10"
20 j0 IN q0 EXITS-SERVER 0
20 j0 IN q0 DEPART-VIA out0.wl
20 j1 IN q0 ENTERS-SERVER 0
20 j1 IN q0 TASK-START 0 "W 10"
30 j1 IN q0 TASK-END 0 "W 10"
30 j1 IN q0 EXITS-SERVER 0
30 j1 IN q0 DEPART-VIA out0.wl
```

`./filter_by_job.py --events events.log --jobs 1`:

```text
10 j1 IN q0 ARRIVE-VIA in0.wl
20 j1 IN q0 ENTERS-SERVER 0
20 j1 IN q0 TASK-START 0 "W 10"
30 j1 IN q0 TASK-END 0 "W 10"
30 j1 IN q0 EXITS-SERVER 0
30 j1 IN q0 DEPART-VIA out0.wl
```

## Pipeline

```bash
./simple-queue-sim --config qconf.csv --qmet runs/qmet.csv --events runs/events.log
python filter_by_job.py --events runs/events.log --jobs 0,1 --out runs/j0_j1_events.log
```

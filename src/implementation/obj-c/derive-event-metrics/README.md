# derive-event-metrics

CLI that turns the simulator's event log into **per-visit job metrics**
(PDF §C, "Derived Job Metrics").

Design pseudocode: [`src/design/obj-c/events/derive-emetrics.pseudo`](../../../design/obj-c/events/derive-emetrics.pseudo)

## Usage

```bash
python derive_event_metrics.py --events events.log [--out emetrics.csv] [--verbose]
```

| Flag | Meaning |
|------|---------|
| `--events` | Event log written by `simple-queue-sim` / `multi-queue-sim` (required) |
| `--out` | Output CSV; default `-` writes to stdout |
| `-v` | Print counts and per-line warnings to stderr |

Standard library only.

## Output

One row per **visit** of a job to a queue system. A job that passes through three
queues produces three rows; a job that loops back into the same queue produces a row
per visit. Rows are written in the order visits complete (streaming, so large logs
do not need to fit in memory).

```csv
Job-id,Queue-sys-id,arrival-time,time-in-queue,time-in-service,response-time,turnaround-time
```

| Column | Definition (event tokens in this queue) |
|--------|------------------------------------------|
| `Job-id` | Job id from the log |
| `Queue-sys-id` | Queue system id (`q0`, `q1`, …) |
| `arrival-time` | Time step of `ARRIVE-VIA` |
| `time-in-queue` | `ENTERS-SERVER` − `ARRIVE-VIA` (waiting for a server) |
| `time-in-service` | `EXITS-SERVER` − `ENTERS-SERVER` |
| `response-time` | Time until the job first enters a server (equals `time-in-queue`) |
| `turnaround-time` | `time-in-queue` + `time-in-service` = `EXITS-SERVER` − `ARRIVE-VIA` |

Visits rejected with `ERROR QUEUE-FULL` never entered a server, so they have no
row; the count is printed to stderr (drops are also visible in `qmet.csv` as
`num-of-errors`). Visits still open when the log ends (job waiting or in service when
the run stopped) are likewise counted and skipped.

## Worked example

Input (`src/examples/obj-b/events-single.log`, the PDF walkthrough):

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
0 j0 IN q0 ENTERS-SERVER 0
...
20 j0 IN q0 EXITS-SERVER 0
20 j0 IN q0 DEPART-VIA out0.wl
20 j1 IN q0 ENTERS-SERVER 0
...
```

`python derive_event_metrics.py --events events-single.log`:

```csv
Job-id,Queue-sys-id,arrival-time,time-in-queue,time-in-service,response-time,turnaround-time
j0,q0,0,0,20,0,20
j1,q0,10,10,10,10,20
j2,q0,20,10,30,10,40
```

These match `src/examples/obj-c/events/emetrics-ex.csv`. The downstream
`plot-derive-event-metrics` tool reads this file with `--hist="arrival-time"` or
`--scat="arrival-time,response-time"`.

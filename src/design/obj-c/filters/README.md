# Log Filters: Queue and Job

## Goal

In a queue simulation, the raw output logs contain interleaved data from all queues and jobs. The filter tools extract specific slices of this data for targeted analysis.

* **filter-by-queue:** isolates the system metrics for a specific queue ID (`q_id`) from the global `qmet.csv`.
* **filter-by-job:** isolates the lifecycle events for a specific job ID (`job_id`) from the global `events.log`.

## CLI sketch

Both tools accept the raw log and the target identifier, outputting a subset file.

```bash
# 1. Filter metrics by Queue ID
filter-by-queue \
  --qmet qmet.csv \
  --qid Q_ID \               # e.g., q0
  [--out qX_metrics.csv]      # default: <Q_ID>_metrics.csv

# 2. Filter events by Job ID
filter-by-job \
  --events events.log \
  --job JOB_ID \              # e.g., j1
  [--out jX_events.log]       # default: <JOB_ID>_events.log

```

## Worked example (tiny)

**Queue Filter:**
Input `qmet.csv`:
```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,q0,1,1,0
0,q1,0,0,0
1,q0,2,1,0
```

Command: `filter-by-queue --qmet qmet.csv --qid q0`
Output `q0_metrics.csv`:
```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,q0,1,1,0
1,q0,2,1,0
```

**Job Filter:**
Input `events.log`:
```text
0 j0 IN q0 ARRIVE-VIA in0.wl
0 j0 IN q0 ENTERS-SERVER 0
0 j0 IN q0 TASK-START 0 "W 10"
10 j1 IN q0 ARRIVE-VIA in0.wl
10 j0 IN q0 TASK-END 0 "W 10"
10 j0 IN q0 LEAVES-SERVER 0
10 j0 IN q0 DEPART-VIA out0.wl
10 j1 IN q0 ENTERS-SERVER 0
10 j1 IN q0 TASK-START 0 "W 10"
...
```

Command: `filter-by-job --events events.log --job j1`
Output `j1_events.log`:
```text
10 j1 IN q0 ARRIVE-VIA in0.wl
10 j1 IN q0 ENTERS-SERVER 0
10 j1 IN q0 TASK-START 0 "W 10"
...
```

## Implementation plan

1. Parse CLI parameters.
2. **Queue filter:** Use `pandas` to read `qmet.csv`, apply a dataframe boolean mask (`df[df['queue-sys-id'] == qid]`), and export via `to_csv(index=False)`.
3. **Job filter:** Since the event log is space-delimited text and tasks can contain spaces, `pandas` might struggle with formatting. A standard Python file reader is safer: check if the second token in each line matches the target `job_id`.
4. Write the filtered streams to the `--out` files.
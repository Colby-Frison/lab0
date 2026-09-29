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
  --qid Q_ID[,Q_ID...] \     # e.g., 0 or 0,2 (q0 is accepted as 0)
  [--out q0_metrics.csv]      # default: stdout

# 2. Filter events by Job ID
filter-by-job \
  --events events.log \
  --jobs JOB_ID[,JOB_ID...] \ # e.g., j1 or 1 (1 is accepted as j1)
  [--out j1_events.log]       # default: stdout

```

## Worked example (tiny)

**Queue Filter:**
Input `qmet.csv`:
```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
0,1,0,0,0
1,0,2,1,0
```

The simulator writes numeric queue ids (`q0` in the config becomes `0` in `qmet.csv`).

Command: `filter-by-queue --qmet qmet.csv --qid 0 --out q0_metrics.csv`
Output `q0_metrics.csv`:
```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
1,0,2,1,0
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

Command: `filter-by-job --events events.log --jobs j1 --out j1_events.log`
Output `j1_events.log`:
```text
10 j1 IN q0 ARRIVE-VIA in0.wl
10 j1 IN q0 ENTERS-SERVER 0
10 j1 IN q0 TASK-START 0 "W 10"
...
```

## Implementation plan

1. Parse CLI parameters.
2. **Queue filter:** Use `pandas` to read `qmet.csv`, read every cell as a string (`dtype=str`), apply a dataframe boolean mask (`df[df['queue-sys-id'].isin(qids)]`), and export via `to_csv(index=False)`.
3. **Job filter:** Since the event log is space-delimited text and tasks can contain spaces, `pandas` might struggle with formatting. A standard Python file reader is safer: check if the second token in each line matches one of the target job ids exactly (not any token, and not a substring, so `j1` never matches `j10`).
4. Write the filtered streams to the `--out` files.
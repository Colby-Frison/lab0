# filter-by-queue

CLI that keeps only the `qmet.csv` rows of one or more queue systems (PDF §C,
"Filters"). Use it to look at a single queue of a multi-queue run, or to feed one
queue's rows into USE / plotting tools.

Design notes: [`src/design/obj-c/filters/README.md`](../../../design/obj-c/filters/README.md)

## Usage

```bash
./filter_by_queue.py --qmet qmet.csv --qid 0[,1,...] [--out qmetout.csv] [--verbose]
```

| Flag | Meaning |
|------|---------|
| `--qmet` | `qmet.csv` written by `simple-queue-sim` / `multi-queue-sim`  (required); `-` reads stdin |
| `--qid` | Queue id, or a comma-separated list such as `0,2` (required) |
| `--out` | Output CSV; default `-` writes to stdout |
| `-v` | Print the requested ids, the ids found in the file, and rows in/out to stderr |

Requires `pandas`. The script starts with `#!/usr/bin/env python3`, so activate the
project venv first (`source .venv/bin/activate` from the repo root), or run it
explicitly with `python filter_by_queue.py ...`.

## Queue ids

The simulator writes **numeric** ids to `qmet.csv`: `q0` in the config becomes `0`.
`--qid` accepts both forms and normalizes the argument to the numeric one (`q0`,
`Q0`, `0` and `007` all mean `0`). The `queue-sys-id` column in the file is compared
exactly as it is.

## Output

The output has the same header, columns and cell text as the input. Only rows
whose `queue-sys-id` is in `--qid` are kept, in their original (time-step) order. If
several queues are requested, their rows stay interleaved by time step.

- The header is always written; if nothing matches, the output is header only.
- A requested id that is not in the file prints a warning to stderr listing the
  available ids. The exit code is still `0`.
- An unreadable or empty file, a missing `queue-sys-id` column, or an invalid `--qid`
  (e.g. `abc`) stops with an error message and a non-zero exit code.

## Worked example

Input `qmet.csv`:

```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
0,1,0,0,0
0,2,0,0,0
1,0,2,1,0
1,1,1,1,0
1,2,0,0,0
```

`./filter_by_queue.py --qmet qmet.csv --qid 0`:

```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
1,0,2,1,0
```

`./filter_by_queue.py --qmet qmet.csv --qid q0,2 --out q0_q2.csv` writes:

```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
0,2,0,0,0
1,0,2,1,0
1,2,0,0,0
```

## Pipeline

```bash
./simple-queue-sim --config qconf.csv --qmet runs/qmet.csv --events runs/events.log
python filter_by_queue.py --qmet runs/qmet.csv --qid 0 --out runs/q0_metrics.csv

# or in a pipe
cat runs/qmet.csv | python filter_by_queue.py --qmet - --qid 1 | head
```

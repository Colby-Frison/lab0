# compute-use

CLI that turns `qmet.csv` into per-queue USE windows (PDF §C, "Compute USE").

Design notes: [`src/design/obj-c/USE/README.md`](../../../design/obj-c/USE/README.md)

## Usage

```bash
python compute_use.py --qmet qmet.csv --config qconf.csv [--out quse.csv] [--verbose]
```

| Flag | Meaning |
|------|---------|
| `--qmet` | `qmet.csv` written by the simulator (required) |
| `--config` | `qconf.csv`, used for `Num. Servers` (required) |
| `--out` | Output CSV; default `-` writes to stdout |
| `-v` | Print the queues and the row counts to stderr |

Requires `pandas`.

## Windows

For each queue, looking back over 10, 100, and 1000 of that queue's own steps:

| Column | Value |
|--------|--------|
| `Utilization(W)` | Mean of `num-jobs-in-service / Num. Servers` |
| `Saturation(W)` | Mean of `num-jobs-in-queue` (jobs waiting) |
| `Errors(W)` | Sum of `num-of-errors` |

A window that has not filled yet uses the steps that exist. `q0` in the config matches `0` in `qmet.csv`. A queue present in `qmet.csv` and missing from the config is an error.

## Output

```csv
time-step,queue-sys-id,Utilization(10),Saturation(10),Errors(10),Utilization(100),Saturation(100),Errors(100),Utilization(1000),Saturation(1000),Errors(1000)
```

Rows are ordered by time step, then queue id. Numbers are rounded to 6 decimal places. Error totals stay integers.

## Worked example

Config: one server on `q0`.

```csv
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,0,0,0
1,0,2,1,0
2,0,1,1,1
```

At step 2 every window is the same three steps: utilization $(0+1+1)/3$, saturation $(0+2+1)/3$, errors $1$.

```csv
time-step,queue-sys-id,Utilization(10),Saturation(10),Errors(10),Utilization(100),Saturation(100),Errors(100),Utilization(1000),Saturation(1000),Errors(1000)
0,0,0.0,0.0,0,0.0,0.0,0,0.0,0.0,0
1,0,0.5,1.0,0,0.5,1.0,0,0.5,1.0,0
2,0,0.666667,1.0,1,0.666667,1.0,1,0.666667,1.0,1
```

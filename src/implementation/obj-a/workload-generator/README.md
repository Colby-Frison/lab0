# Workload Generator

CLI tool that emits a synthetic workload CSV for the queueing lab.

## Usage

```bash
python workload_generator.py
  --interval START:END
  --dist {fixed,uniform,normal,geometric,poisson}
  [distribution stats\]
  [--task-mode {fixed,dist}]
  [--seed N]
  [--out PATH]
```

`--interval` is **inclusive** (`0:2` → time steps 0, 1, 2). Without `--out`, CSV is written to stdout.

### Distribution stats


| `--dist`    | Required flags                      |
| ----------- | ----------------------------------- |
| `fixed`     | `--fixed-jobs N`                    |
| `uniform`   | `--low L --high H` (inclusive ints) |
| `normal`    | `--mu M --sigma S`                  |
| `geometric` | `--p P` in `(0, 1]`                 |
| `poisson`   | `--lam LAMBDA`                      |


### Task / work mode

- `--task-mode dist` (default): task count and each task’s `W N` are sampled from the same distribution (clamped to ≥ 1).
- `--task-mode fixed`: use `--fixed-tasks K` and `--fixed-work N`.

### Examples

```bash
# Uniform arrivals/tasks/work over steps 0..49
python workload_generator.py --interval 0:49 --dist uniform --low 1 --high 5 --seed 42 --out wl.csv

# Fixed 2 jobs/step, each with one task of work 10
python workload_generator.py --interval 0:20 --dist fixed --fixed-jobs 2 \
  --task-mode fixed --fixed-tasks 1 --fixed-work 10 --out wl.csv

# Poisson with lambda=2
python workload_generator.py --interval 0:49 --dist poisson --lam 2 --seed 1 --out wl-poisson.csv
```


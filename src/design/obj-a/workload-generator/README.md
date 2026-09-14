# Workload generator

## Goal

Given a time **interval** and a **distribution** (plus distribution statistics), emit a synthetic workload of sorted jobs. At each time step in the interval, draw how many jobs arrive from the distribution. Optionally, task counts and per-task work values are either **fixed** or drawn from the **same** distribution family.

## CLI sketch

All parameters are command-line arguments (required + optional), e.g.:

```text
workload-generator \
  --interval START:END \
  --dist {fixed,uniform,normal,geometric,poisson} \
  [--seed SEED] \
  [--out PATH] \
  # distribution stats (which flags are required depends on --dist)
  [--low L --high H]          # uniform (inclusive ints)
  [--mu M --sigma S]          # normal
  [--p P]                     # geometric success probability
  [--lam LAMBDA]              # poisson mean
  [--fixed-jobs N]            # fixed: jobs per step
  # task / work options
  [--task-mode {fixed,dist}]  # default: dist (same family as --dist)
  [--fixed-tasks K]           # if task-mode=fixed: tasks per job
  [--fixed-work N]            # if task-mode=fixed: W N for each task
```

Notes:

- `--interval START:END` defines inclusive time steps `[START, END)` or `[START, END]` — pick one convention and document it in the implementation README (recommend inclusive `[START, END]` to match “range of time steps” wording).
- Jobs/step, tasks/job, and work-per-task can each use the distribution (lab: “individual tasks … fixed or drawn from the same distribution”).
- Non-negative clamping: jobs/step may be 0; tasks/job and work `N` must be ≥ 1 when a job is emitted.
- Output default: stdout or `--out wl.csv`.

## Distributions (jobs / tasks / work)

Align with `examples/obj-a` sketches and `examples/README.md`:

| Dist | Parameters | Intended shape |
|------|------------|----------------|
| Fixed | constant `k` | Always `k` (baseline / debugging) |
| Uniform | inclusive `[low, high]` | Equal chance of light vs heavy load |
| Normal | `μ`, `σ` | Cluster around mean; rare extremes; clamp ≥ 0 (jobs) or ≥ 1 (tasks/work) |
| Geometric | success `p` | Many small/zero values, occasional spikes (`failures before success`; use `geo(p)-1` if 0 should be allowed for jobs/step) |
| Poisson | `λ` | Natural bursty arrivals around mean rate |

Suggested mapping when `--task-mode=dist`:

1. `num_jobs = sample(dist)` for this time step (0 allowed)
2. For each job: `num_tasks = max(1, sample(dist))`
3. For each task `tid`: `work = max(1, sample(dist))` → `"tid: W work"`

## Worked example (tiny)

Input:

```text
--interval 0:2 --dist uniform --low 1 --high 2 \
  --task-mode fixed --fixed-tasks 1 --fixed-work 3 --seed 1
```

Possible output (illustrative):

```csv
Job Id,arrival time,Tasks
j0,0,"[""0: W 3""]"
j1,0,"[""0: W 3""]"
j2,1,"[""0: W 3""]"
j3,2,"[""0: W 3""]"
j4,2,"[""0: W 3""]"
```

Compare shape (variable tasks/work) against `examples/obj-a/wl-uniform.csv`.

## Implementation plan

1. Parse CLI (`argparse`); validate that the stats required for `--dist` are present.
2. Implement `draw_*` helpers (numpy or stdlib `random`).
3. Emit CSV with pandas or csv module; quote `Tasks` consistently with examples.
4. Unit-smoke: regenerate with a fixed seed and compare column schema + sorted arrivals to example files (exact rows need not match unless seed/params are locked to those examples).

## Resources

- Lab PDF: *Queue Lab* §A (workload schema, generator I/O)
- `examples/obj-a/wl-*.csv`, `examples/README.md` (distribution intent)
- `Documentation/Resources/example/q_ex-1.py` (how jobs later enter a discrete-time sim)
- Python: `argparse`, `random` / `numpy.random`, `csv` / `pandas`
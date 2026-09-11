# Objective A — Design: Workload Generator & Visualizer

## Premise

This lab builds a discrete-time queueing toolkit. Jobs arrive over time steps, wait in queues, and are processed by servers that mutate each job’s task list until the job is complete (`Tasks == []`).

**Objective A** is the front door of that pipeline: produce synthetic workloads and inspect them before they feed the simple queue simulator (Obj B) as source files (`in0.wl` / CSV).

Deliverables (from `tasks.md` / Queue Lab slides):

| Tool | Path | Role |
|------|------|------|
| Workload generator | `implementation/obj-a/workload-generator/` | CLI: interval + distribution (+ stats) → sorted synthetic workload |
| Workload visualizer | `implementation/obj-a/workload-visualizer/` | CLI: workload file → histogram and/or scatter PNG |

Language: Python (or R) is appropriate; matplotlib + pandas cover the visualizer. Keep the **workload file format** stable so Obj B/C/E can read the same CSVs.

---

## Shared workload format

Every workload (input to a queue **source**, or completed jobs at a **sink**) uses the same schema:

| Column | Meaning |
|--------|---------|
| `Job Id` | Stable id (`j0`, `j1`, …) |
| `arrival time` | Time step the job enters the system (source) **or** leaves the system (completed/sink) |
| `Tasks` | Ordered list of tasks as strings `"<tid>: W N"` where `N` is positive work |

Rules from the lab PDF:

- Tasks look like: `["0: W 10", "1: W 10"]`
- If `Tasks == []`, the job is done
- Jobs in a generated workload must be **sorted** (by arrival time, then job id)

Example (source-style, unfinished work):

```csv
Job Id,arrival time,Tasks
j0,0,"[""0: W 10"", ""1: W 10""]"
j1,10,"[""0: W 10""]"
j2,20,"[""0: W 10"", ""1: W 10"", ""2: W 10""]"
```

Example (completed/sink-style — same columns, empty tasks, arrival = departure time):

```csv
Job Id,arrival time,Tasks
j0,20,[]
j1,30,[]
j2,60,[]
```

Repo examples to validate against: `examples/obj-a/wl-{uniform,normal,geometric,poisson}.csv`.

---

## 1. Workload generator

### Goal

Given a time **interval** and a **distribution** (plus distribution statistics), emit a synthetic workload of sorted jobs. At each time step in the interval, draw how many jobs arrive from the distribution. Optionally, task counts and per-task work values are either **fixed** or drawn from the **same** distribution family.

### CLI sketch

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

### Distributions (jobs / tasks / work)

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

### Pseudocode

```text
function generate_workload(interval, dist, stats, task_mode, fixed_task_opts, seed):
    rng = seeded RNG(seed)
    jobs = []
    next_id = 0

    for t in time_steps(interval):
        n_jobs = draw_nonneg_int(rng, dist, stats)   # jobs arriving at t

        for _ in 1..n_jobs:
            if task_mode == fixed:
                n_tasks = fixed_task_opts.k
                works   = [fixed_task_opts.w] * n_tasks
            else:
                n_tasks = max(1, draw_nonneg_int(rng, dist, stats))
                works   = [max(1, draw_nonneg_int(rng, dist, stats))
                           for _ in 1..n_tasks]

            tasks = [f"{tid}: W {works[tid]}" for tid in 0..n_tasks-1]
            jobs.append({ id: f"j{next_id}", arrival: t, Tasks: tasks })
            next_id += 1

    sort jobs by (arrival, id)
    write CSV(jobs)
```

### Worked example (tiny)

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

### Implementation plan

1. Parse CLI (`argparse`); validate that the stats required for `--dist` are present.
2. Implement `draw_*` helpers (numpy or stdlib `random`).
3. Emit CSV with pandas or csv module; quote `Tasks` consistently with examples.
4. Unit-smoke: regenerate with a fixed seed and compare column schema + sorted arrivals to example files (exact rows need not match unless seed/params are locked to those examples).

### Resources

- Lab PDF: *Queue Lab* §A (workload schema, generator I/O)
- `examples/obj-a/wl-*.csv`, `examples/README.md` (distribution intent)
- `Documentation/Resources/example/q_ex-1.py` (how jobs later enter a discrete-time sim)
- Python: `argparse`, `random` / `numpy.random`, `csv` / `pandas`

---

## 2. Workload visualizer

### Goal

Read a workload CSV and produce either:

- a **histogram** of one column (typically `arrival time`), or
- a **scatter** of two columns (typically `arrival time` vs `len(Tasks)`)

Optional plot cosmetics: title, x/y limits, output path. Matplotlib + pandas do the heavy lifting (per PDF).

### CLI sketch (matches lab slides)

```text
# Histogram: jobs per arrival-time bin
workload-visualizer workload.csv \
  --hist "arrival time" \
  --bins N \
  [--title T] [--xlim A:B] [--ylim C:D] \
  --out hist.png

# Scatter: arrival time vs number of tasks in each job
workload-visualizer workload.csv \
  --scat "arrival time,len(Tasks)" \
  [--title T] [--xlim A:B] [--ylim C:D] \
  --out scat.png
```

Notes:

- `--hist` and `--scat` are mutually exclusive modes.
- `len(Tasks)` is a **derived** column: parse the Tasks cell (JSON-like list) and take its length. It is not stored in the CSV.
- Bin count applies to histogram mode only.
- Output PNG path via `--out`.

### Pseudocode

```text
function visualize(path, mode, columns, bins, style, out):
    df = pandas.read_csv(path)
    df["len(Tasks)"] = df["Tasks"].map(parse_task_list).map(len)

    if mode == hist:
        col = columns[0]          # e.g. "arrival time"
        ax = df[col].plot.hist(bins=bins)
        # optional: one bin per time step if bins == unique arrivals
    else:  # scatter
        x, y = columns[0], columns[1]
        ax = df.plot.scatter(x=x, y=y)

    apply style (title, xlim, ylim)
    savefig(out)
```

### Expected plot semantics (from example sketches)

Reference scripts/images: `examples/obj-a/hist.py`, `scat.py`, `histogram_*.png`, `scatter_*.png`.

| Mode | X | Y | What you should see |
|------|---|---|---------------------|
| Hist | arrival time | count of jobs | Burstiness / idle gaps for Poisson & geometric; flatter spread for uniform; tight band for fixed/normal |
| Scatter | arrival time | len(Tasks) | How job “size” (task count) varies over time; denser at small y for geometric/poisson |

### Worked example

```text
workload-visualizer examples/obj-a/wl-poisson.csv \
  --hist "arrival time" --bins 50 --out /tmp/poisson_hist.png

workload-visualizer examples/obj-a/wl-poisson.csv \
  --scat "arrival time,len(Tasks)" --out /tmp/poisson_scat.png
```

Sanity-check against `histogram_poisson.png` / `scatter_poisson.png` (shape, not pixel-identical).

### Implementation plan

1. CSV load + robust Tasks parser (handle double-quoted JSON-ish lists in examples).
2. Add derived `len(Tasks)`.
3. Hist / scatter branches; write PNG.
4. Smoke-test on all four `wl-*.csv` examples.

### Resources

- Lab PDF: *Queue Lab* §A visualizer (CLI flags `--hist`, `--scat`, `--out`)
- `examples/obj-a/hist.py`, `scat.py` (sketch generators)
- pandas `DataFrame.plot.hist` / `plot.scatter`; matplotlib `savefig`

---

## How Obj A fits the rest of the lab

```text
[workload-generator] --> wl.csv
                            |
                            +--> [workload-visualizer] --> hist/scat PNGs
                            |
                            +--> Obj B source (e.g. in0.wl)
                                    --> qmet.csv, job.log, sink workload
                                    --> Obj C filters / USE / metrics / traces
```

- Generator creates the **source workload** the queue reads.
- Visualizer is the first analysis tool: confirm arrivals and job sizes look like the intended distribution before trusting simulation results.
- Sink outputs reuse the same CSV schema with empty `Tasks` (departure time in the arrival column) — the visualizer should still accept those files for completed-job plots later.

---

## Suggested repo layout

```text
src/design/obj-a/README.md              # this document
src/implementation/obj-a/
  workload-generator/                   # CLI entrypoint + README usage
  workload-visualizer/
src/examples/obj-a/                     # golden-ish samples + sketch plots
```

---

## Acceptance checklist

- [ ] Generator accepts interval, distribution, stats, and optional fixed-vs-dist task mode via CLI
- [ ] Output CSV matches schema; jobs sorted by arrival; task strings `"tid: W N"`
- [ ] Visualizer supports `--hist` (column + bins) and `--scat` (two columns including `len(Tasks)`)
- [ ] Visualizer accepts optional title / axis limits and writes `--out` PNG
- [ ] Tools run cleanly on `examples/obj-a/wl-*.csv` and produce plots consistent with sketch intent

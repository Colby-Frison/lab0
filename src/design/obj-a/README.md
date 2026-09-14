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

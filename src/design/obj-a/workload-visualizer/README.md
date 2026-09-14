# Workload visualizer

## Goal

Read a workload CSV and produce either:

- a **histogram** of one column (typically `arrival time`), or
- a **scatter** of two columns (typically `arrival time` vs `len(Tasks)`)

Optional plot cosmetics: title, x/y limits, output path. Matplotlib + pandas do the heavy lifting (per PDF).

## CLI sketch (matches lab slides)

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

## Expected plot semantics (from example sketches)

Reference scripts/images: `examples/obj-a/hist.py`, `scat.py`, `histogram_*.png`, `scatter_*.png`.

| Mode | X | Y | What you should see |
|------|---|---|---------------------|
| Hist | arrival time | count of jobs | Burstiness / idle gaps for Poisson & geometric; flatter spread for uniform; tight band for fixed/normal |
| Scatter | arrival time | len(Tasks) | How job “size” (task count) varies over time; denser at small y for geometric/poisson |

## Worked example

```text
workload-visualizer examples/obj-a/wl-poisson.csv \
  --hist "arrival time" --bins 50 --out /tmp/poisson_hist.png

workload-visualizer examples/obj-a/wl-poisson.csv \
  --scat "arrival time,len(Tasks)" --out /tmp/poisson_scat.png
```

Sanity-check against `histogram_poisson.png` / `scatter_poisson.png` (shape, not pixel-identical).

## Implementation plan

1. CSV load + robust Tasks parser (handle double-quoted JSON-ish lists in examples).
2. Add derived `len(Tasks)`.
3. Hist / scatter branches; write PNG.
4. Smoke-test on all four `wl-*.csv` examples.

## Resources

- Lab PDF: *Queue Lab* §A visualizer (CLI flags `--hist`, `--scat`, `--out`)
- `examples/obj-a/hist.py`, `scat.py` (sketch generators)
- pandas `DataFrame.plot.hist` / `plot.scatter`; matplotlib `savefig`
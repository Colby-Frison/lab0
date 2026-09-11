# Objective A — Implementation

Synthetic workload tools for the queueing lab.

| Tool | Directory | Entry point |
|------|-----------|-------------|
| Workload generator | `workload-generator/` | `workload_generator.py` |
| Workload visualizer | `workload-visualizer/` | `workload_visualizer.py` |

See each subdirectory README for CLI details. Design notes live in `src/design/obj-a/README.md`.

## Quick start

```bash
# Generate a Poisson workload
python workload-generator/workload_generator.py \
  --interval 0:49 --dist poisson --lam 2 --seed 1 --out /tmp/wl.csv

# Histogram of arrivals
python workload-visualizer/workload_visualizer.py /tmp/wl.csv \
  --hist "arrival time" --bins 50 --out /tmp/hist.png

# Scatter of task counts
python workload-visualizer/workload_visualizer.py /tmp/wl.csv \
  --scat "arrival time,len(Tasks)" --out /tmp/scat.png
```

Requires Python 3 with `pandas` and `matplotlib` (visualizer).

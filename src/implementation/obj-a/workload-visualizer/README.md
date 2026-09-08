# Workload Visualizer

CLI tool that plots a workload CSV as a histogram or scatter PNG.

## Usage

```bash
# Histogram of arrival times
python workload_visualizer.py WORKLOAD.csv
  --hist "arrival time"
  --bins N
  [--title T] [--xlim A:B] [--ylim C:D]
  --out hist.png

# Scatter: arrival time vs number of tasks
python workload_visualizer.py WORKLOAD.csv
  --scat "arrival time,len(Tasks)"
  [--title T] [--xlim A:B] [--ylim C:D]
  --out scat.png
```

`--hist` and `--scat` are mutually exclusive. `len(Tasks)` is derived by parsing the `Tasks` column.

### Examples

```bash
python workload_visualizer.py ../../../examples/obj-a/wl-poisson.csv
  --hist "arrival time" --bins 50 --out poisson_hist.png

python workload_visualizer.py ../../../examples/obj-a/wl-poisson.csv
  --scat "arrival time,len(Tasks)" --out poisson_scat.png
```

Depends on `pandas` and `matplotlib`.
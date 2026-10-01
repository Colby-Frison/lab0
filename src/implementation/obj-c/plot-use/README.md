# plot-use

CLI that draws the three USE series from `quse.csv` (PDF §C, "Plot USE").

Design notes: [`src/design/obj-c/USE/README.md`](../../../design/obj-c/USE/README.md)

## Usage

```bash
python plot_use.py --quse quse.csv [--qid 0[,1,...]] [--out use.png] [--title TEXT] [--xlim A:B]
```

| Flag | Meaning |
|------|---------|
| `--quse` | CSV written by `compute-use` (required) |
| `--qid` | One queue, or a comma-separated list. Default: every queue in the file |
| `--out` | PNG path; default `use.png` |
| `--title` | Optional figure title |
| `--xlim` | Time-step bounds `A:B` |

Requires `pandas` and `matplotlib`.

## Figure

Three panels share the time axis. The labels match the slide: Utilization, Saturation, and Error Rate. The error series is the window total from `compute-use` (jobs dropped in the last 10, 100, or 1000 steps).

A light line is the 10-step window, a solid line is 100, and a dark dashed line is 1000. Saturation's 10-step window is a filled area, the same treatment as the course sketch. The legend is drawn once, beside the figure.

One queue uses the slide colors: blue utilization, a yellow saturation area, and a red error rate. Several queues each get their own hue, and the three windows stay shades of that hue. `--qid 0` keeps a single queue when the CSV has many.

```bash
python compute_use.py --qmet runs/qmet.csv --config qconf.csv --out runs/quse.csv
python plot_use.py --quse runs/quse.csv --qid 0 --out runs/use.png --title "Queue q0"
```

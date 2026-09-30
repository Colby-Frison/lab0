# plot-derive-event-metrics

Python visualizer for "C. Events: Plotting Derived Job Metrics" in the lab PDF.
Histogram and scatter plotting are implemented and require `pandas` and `matplotlib`.

```bash
python plot_derive_event_metrics.py emetric.csv plot.png --hist="arrival-time" --bins 25
python plot_derive_event_metrics.py emetric.csv plot.png --hist="response-time" --bins 20 --title "Job response times" --xlim 0:100 --ylim 0:50
python plot_derive_event_metrics.py emetric.csv scatter.png --scat="arrival-time,response-time" --title "Response time by arrival" --xlim 0:100 --ylim 0:50
```

| Argument | Meaning |
| --- | --- |
| `emetrics` | Required positional input CSV filename |
| `out` | Required positional output image filename |
| `--hist COLUMN` | Column for a histogram |
| `--scat X,Y` | Two comma-separated columns for a scatter plot |
| `--bins N` | Positive histogram bin count; default 10 |
| `--title TEXT` | Optional plot title |
| `--xlim A:B` | Optional numeric X-axis limits |
| `--ylim A:B` | Optional numeric Y-axis limits |
| `-h`, `--help` | Display usage |

Exactly one of `--hist` or `--scat` is required. Selected columns must exist and
contain non-empty, finite numeric values; missing or nonnumeric values are errors.
Each CSV row represents one queue visit and contributes one observation. Axis
limits change the displayed viewport, not the data used to calculate bins.
The image is saved to the positional output path without opening a GUI window.
The bin default and axis-limit syntax follow the existing workload visualizer.

Scatter plots use the first selected column for X and the second for Y, preserving
each row's pairing. `--bins` applies only to histograms.

Run `../run-all-tests.ps1` (PowerShell) or `bash ../run-all-tests.sh` (Bash) to run
the full Obj C suite, including histogram and scatter tests. Both runners prefer
the repository's `.venv` when available.

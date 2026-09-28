#!/usr/bin/env python3
"""plot-sys-metrics — Queue Lab Objective C.

Plot the system metrics CSV produced by derive-sys-metrics as two stacked
panels that share the time axis:

    1. Response time (latency) vs time-step: median and average lines with a
       shaded P10–P90 band showing the spread of jobs leaving at each step.
    2. Throughput vs time-step: number of jobs leaving the simulator per step
       (or per window, if derive-sys-metrics was run with --window).

Usage:
    python plot_sys_metrics.py --sysmetrics sysmetrics.csv [--out resplot.png]
                               [--title TEXT] [--xlim A:B] [--ylim A:B] [--no-band]
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REQUIRED_COLUMNS = [
    "time-step",
    "Avg-response-time",
    "median-response-time",
    "10-response-time",
    "90-response-time",
    "throughput",
]

# Colors follow the lab's shared chart palette: two categorical series on the
# latency panel (blue = median, orange = average), a blue wash for the P10–P90
# band, green for the single throughput series, recessive gray chrome.
COLORS = {
    "median": "#2a78d6",
    "average": "#eb6834",
    "band": "#2a78d6",
    "throughput": "#008300",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "ink": "#0b0b0b",
    "muted": "#52514e",
}

MARKER_POINT_LIMIT = 60  # draw point markers only for short series


def parse_pair(value: str) -> tuple[float, float]:
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected A:B")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bounds must be numbers") from exc


def load_sysmetrics(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"sysmetrics CSV missing columns: {missing}")
    if df.empty:
        raise SystemExit("sysmetrics CSV has no rows (no job reached a sink?)")
    return df.sort_values("time-step").reset_index(drop=True)


def _style_axis(ax) -> None:
    ax.grid(True, color=COLORS["grid"], linewidth=1, linestyle="-")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(COLORS["axis"])
    ax.tick_params(colors=COLORS["muted"], labelsize=9)
    ax.yaxis.label.set_color(COLORS["ink"])
    ax.xaxis.label.set_color(COLORS["ink"])
    ax.title.set_color(COLORS["ink"])


def plot_system_metrics(
    df: pd.DataFrame,
    out: str,
    title: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    band: bool = True,
) -> None:
    t = df["time-step"]
    marker = "o" if len(df) <= MARKER_POINT_LIMIT else None

    fig, (ax_lat, ax_tp) = plt.subplots(
        2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
    )

    # --- Panel 1: response time ------------------------------------------ #
    if band:
        ax_lat.fill_between(
            t,
            df["10-response-time"],
            df["90-response-time"],
            color=COLORS["band"],
            alpha=0.15,
            linewidth=0,
            label="P10–P90 band",
        )
    ax_lat.plot(
        t, df["median-response-time"], color=COLORS["median"], linewidth=2,
        marker=marker, markersize=4, label="Median",
    )
    ax_lat.plot(
        t, df["Avg-response-time"], color=COLORS["average"], linewidth=2,
        marker=marker, markersize=4, label="Average",
    )
    ax_lat.set_ylabel("Response time (time steps)")
    ax_lat.set_title("Response time (latency) vs time-step", loc="left", fontsize=11)
    ax_lat.legend(loc="upper left", frameon=False, labelcolor=COLORS["ink"])
    if ylim is not None:
        ax_lat.set_ylim(*ylim)
    else:
        ax_lat.set_ylim(bottom=0)

    # --- Panel 2: throughput --------------------------------------------- #
    ax_tp.plot(
        t, df["throughput"], color=COLORS["throughput"], linewidth=2,
        marker=marker, markersize=4,
    )
    ax_tp.fill_between(t, 0, df["throughput"], color=COLORS["throughput"], alpha=0.12, linewidth=0)
    ax_tp.set_ylabel("Jobs leaving")
    ax_tp.set_xlabel("time-step")
    ax_tp.set_title("Throughput vs time-step", loc="left", fontsize=11)
    ax_tp.set_ylim(bottom=0)

    for ax in (ax_lat, ax_tp):
        _style_axis(ax)
    if xlim is not None:
        ax_tp.set_xlim(*xlim)

    if title:
        fig.suptitle(title, color=COLORS["ink"])
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot response-time percentiles and throughput from a sysmetrics CSV."
    )
    parser.add_argument("--sysmetrics", required=True, help="CSV written by derive-sys-metrics")
    parser.add_argument("--out", default="resplot.png", help="Output PNG path (default: resplot.png)")
    parser.add_argument("--title", default=None, help="Figure title")
    parser.add_argument("--xlim", type=parse_pair, default=None, help="Time-step limits as A:B")
    parser.add_argument("--ylim", type=parse_pair, default=None, help="Response-time limits as A:B")
    parser.add_argument("--no-band", action="store_true", help="Hide the P10–P90 shaded band")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    df = load_sysmetrics(args.sysmetrics)
    plot_system_metrics(df, args.out, args.title, args.xlim, args.ylim, band=not args.no_band)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

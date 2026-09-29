from __future__ import annotations

import argparse
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# Helper Functions
def parse_columns(value: str) -> tuple[str, str]:
    """Parse the two column names supplied to --scat."""
    columns = [column.strip() for column in value.split(",")]
    if len(columns) != 2 or not all(columns):
        raise argparse.ArgumentTypeError("Expected two column names as X,Y")
    return columns[0], columns[1]

def parse_limits(value: str) -> tuple[float, float]:
    """Parse an axis-limit pair using the repository's A:B convention."""
    try:
        lower, upper = value.split(":")
        return float(lower), float(upper)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected numeric axis limits as A:B") from exc

def positive_int(value: str) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Bin count must be a positive integer") from exc
    if count <= 0:
        raise argparse.ArgumentTypeError("Bin count must be a positive integer")
    return count

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot histograms or scatter plots of derived job metrics."
    )
    parser.add_argument("emetrics", help="Input event-metrics CSV path")
    parser.add_argument("out", help="Output plot image path")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--hist", metavar="COLUMN", help="Histogram column, e.g. arrival-time")
    mode.add_argument(
        "--scat", type=parse_columns, metavar="X,Y",
        help="Scatter columns, e.g. arrival-time,response-time",
    )
    parser.add_argument("--bins", type=positive_int, default=10, help="Histogram bin count (default: 10)")
    parser.add_argument("--title", default=None, help="Plot title")
    parser.add_argument("--xlim", type=parse_limits, default=None, metavar="A:B", help="X-axis limits")
    parser.add_argument("--ylim", type=parse_limits, default=None, metavar="A:B", help="Y-axis limits")
    return parser

def numeric_column(data: pd.DataFrame, column: str) -> pd.Series:
    """Require complete numeric observations so scatter pairs stay aligned."""
    if column not in data.columns:
        raise ValueError(f"Unknown metric column: {column!r}")
    try:
        values = pd.to_numeric(data[column], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Metric column {column!r} must contain numeric values") from exc
    if values.empty or values.isna().any() or not all(math.isfinite(v) for v in values):
        raise ValueError(f"Metric column {column!r} must contain non-empty, finite numeric values")
    return values

def plot_histogram(
    data: pd.DataFrame, column: str, bins: int, out: str,
    title: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
) -> None:
    values = numeric_column(data, column)

    fig, ax = plt.subplots(figsize=(10, 5))
    try:
        ax.hist(values, bins=bins, color="skyblue", edgecolor="black")
        ax.set_xlabel(column)
        ax.set_ylabel("Number of queue visits")
        ax.set_title(title if title is not None else f"Job metrics histogram - {column}")

        if xlim is not None:
            ax.set_xlim(*xlim)
        if ylim is not None:
            ax.set_ylim(*ylim)

        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(out, dpi=150)
    finally:
        plt.close(fig)


def plot_scatter(
    data: pd.DataFrame, x: str, y: str, out: str,
    title: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
) -> None:
    x_values = numeric_column(data, x)
    y_values = numeric_column(data, y)
    fig, ax = plt.subplots(figsize=(10, 5))
    try:
        ax.scatter(x_values, y_values, color="coral", edgecolor="black", alpha=0.7)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title if title is not None else f"Job metrics scatter - {x} vs {y}")
        if xlim is not None:
            ax.set_xlim(*xlim)
        if ylim is not None:
            ax.set_ylim(*ylim)
        ax.grid(linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(out, dpi=150)
    finally:
        plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    # Parse inputs
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = pd.read_csv(args.emetrics)
        if args.scat is not None:
            plot_scatter(data, *args.scat, args.out, args.title, args.xlim, args.ylim)
        else:
            plot_histogram(data, args.hist, args.bins, args.out, args.title, args.xlim, args.ylim)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

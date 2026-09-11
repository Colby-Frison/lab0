#!/usr/bin/env python3
"""Workload visualizer for Queue Lab Objective A."""

from __future__ import annotations

import argparse
import ast
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def parse_pair(value: str) -> tuple[float, float]:
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected A:B")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bounds must be numbers") from exc


def parse_task_list(raw) -> list:
    """Parse Tasks cell from workload CSV (JSON or Python-literal list)."""
    if isinstance(raw, list):
        return raw
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    text = str(raw).strip()
    if text == "" or text == "[]":
        return []
    try:
        value = json.loads(text)
        if isinstance(value, list):
            return value
    except json.JSONDecodeError:
        pass
    try:
        value = ast.literal_eval(text)
        if isinstance(value, list):
            return value
    except (ValueError, SyntaxError):
        pass
    raise ValueError(f"could not parse Tasks cell: {raw!r}")


def parse_column_list(value: str) -> list[str]:
    # Allow "arrival time,len(Tasks)" or "arrival time, len(Tasks)"
    parts = [p.strip() for p in value.split(",")]
    if not parts or any(p == "" for p in parts):
        raise argparse.ArgumentTypeError("column list must be non-empty names")
    return parts


def load_workload(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"Job Id", "arrival time", "Tasks"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"workload missing columns: {sorted(missing)}")
    df["len(Tasks)"] = df["Tasks"].map(parse_task_list).map(len)
    return df


def apply_style(ax, title: str | None, xlim, ylim) -> None:
    if title:
        ax.set_title(title)
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(True, linestyle="--", alpha=0.5)


def plot_histogram(df: pd.DataFrame, column: str, bins: int, title, xlim, ylim, out: str) -> None:
    if column not in df.columns:
        raise SystemExit(f"unknown histogram column: {column!r}")
    fig, ax = plt.subplots(figsize=(10, 5))
    data = df[column]
    ax.hist(data, bins=bins, color="skyblue", edgecolor="black", alpha=0.9)
    ax.set_xlabel(column)
    ax.set_ylabel("Number of Jobs")
    if not title:
        title = f"Workload Histogram — {column}"
    apply_style(ax, title, xlim, ylim)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_scatter(
    df: pd.DataFrame, x: str, y: str, title, xlim, ylim, out: str
) -> None:
    for col in (x, y):
        if col not in df.columns:
            raise SystemExit(f"unknown scatter column: {col!r}")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(
        df[x],
        df[y],
        color="coral",
        edgecolor="black",
        alpha=0.7,
        s=30,
    )
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    if not title:
        title = f"Workload Scatter — {x} vs {y}"
    apply_style(ax, title, xlim, ylim)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Visualize a queueing workload CSV (histogram or scatter)."
    )
    parser.add_argument("workload", help="Path to workload CSV")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--hist",
        metavar="COLUMN",
        help='Histogram column, e.g. "arrival time"',
    )
    mode.add_argument(
        "--scat",
        type=parse_column_list,
        metavar="X,Y",
        help='Scatter columns, e.g. "arrival time,len(Tasks)"',
    )
    parser.add_argument("--bins", type=int, default=10, help="Histogram bin count")
    parser.add_argument("--title", default=None, help="Plot title")
    parser.add_argument("--xlim", type=parse_pair, default=None, help="X limits as A:B")
    parser.add_argument("--ylim", type=parse_pair, default=None, help="Y limits as A:B")
    parser.add_argument("--out", required=True, help="Output PNG path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.hist is not None and args.bins < 1:
        raise SystemExit("--bins must be >= 1")
    if args.scat is not None and len(args.scat) != 2:
        raise SystemExit("--scat requires exactly two columns: X,Y")

    df = load_workload(args.workload)

    if args.hist is not None:
        plot_histogram(df, args.hist, args.bins, args.title, args.xlim, args.ylim, args.out)
    else:
        plot_scatter(
            df, args.scat[0], args.scat[1], args.title, args.xlim, args.ylim, args.out
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

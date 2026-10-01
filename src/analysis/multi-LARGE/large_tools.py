#!/usr/bin/env python3
"""Analysis helpers for Objective F (LARGE): 6,474 AS queues.

Per-queue plots from multi-SMALL do not work for thousands of queues, so these
helpers aggregate over all ASes (utilization vs degree, utilization CDF, drops
per degree class) and zoom in on the busiest few. Styling, loading and USE
come from multi-SMALL's ``analysis_tools.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "multi-SMALL"))

import analysis_tools as at  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402  (analysis_tools selects the Agg backend)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DEGREE_CLASSES = ([0, 1, 2, 9, 99, 100_000], ["1", "2", "3-9", "10-99", "100+"])


# --------------------------------------------------------------------------- #
# qmet.csv aggregation (too large to load at once: queues x steps rows)
# --------------------------------------------------------------------------- #
def aggregate_qmet(path: Path, steady: tuple[int, int], chunksize: int = 2_000_000) -> pd.DataFrame:
    """Per queue: mean busy servers and mean waiting over ``steady``, total errors over the run."""
    lo, hi = steady
    parts: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, chunksize=chunksize):
        errors = chunk.groupby("queue-sys-id")["num-of-errors"].sum()
        s = chunk[(chunk["time-step"] >= lo) & (chunk["time-step"] < hi)]
        g = s.groupby("queue-sys-id").agg(
            busy_sum=("num-jobs-in-service", "sum"),
            wait_sum=("num-jobs-in-queue", "sum"),
            steps=("time-step", "size"),
        )
        parts.append(g.join(errors.rename("errors"), how="outer").fillna(0))
    total = pd.concat(parts).groupby(level=0).sum()
    agg = pd.DataFrame(
        {
            "busy": total["busy_sum"] / total["steps"].clip(lower=1),
            "waiting": total["wait_sum"] / total["steps"].clip(lower=1),
            "errors": total["errors"].astype(int),
        }
    )
    agg.index = "q" + agg.index.astype(int).astype(str)
    return agg


def with_servers(agg: pd.DataFrame, servers: dict[str, int], degree: dict[str, int]) -> pd.DataFrame:
    df = agg.copy()
    df["servers"] = [servers[q] for q in df.index]
    df["degree"] = [degree[q] for q in df.index]
    df["utilization"] = df["busy"] / df["servers"]
    return df


def top_queues(df: pd.DataFrame, k: int = 5) -> list[str]:
    """The ``k`` busiest ASes by utilization."""
    return list(df.sort_values("utilization", ascending=False).index[:k])


def degree_class(degree: pd.Series) -> pd.Series:
    bins, labels = DEGREE_CLASSES
    return pd.cut(degree, bins, labels=labels)


# --------------------------------------------------------------------------- #
# Plots
# --------------------------------------------------------------------------- #
def _save(fig, out: Path, title: str) -> None:
    fig.suptitle(title, x=0.01, ha="left", color=at.PALETTE["ink"])
    fig.tight_layout()
    fig.savefig(out, dpi=at.DPI)
    plt.close(fig)


def plot_util_vs_degree(df: pd.DataFrame, out: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(df["degree"], df["utilization"], s=6, alpha=0.4, color=at.PALETTE["blue"], linewidths=0)
    ax.set_xscale("log")
    ax.set_xlabel("AS degree (links)")
    ax.set_ylabel("utilization (busy servers / servers)")
    ax.set_ylim(0, 1.02)
    at.style_axis(ax)
    _save(fig, out, title)


def plot_util_cdf(df: pd.DataFrame, out: Path, title: str) -> None:
    u = np.sort(df["utilization"].to_numpy())
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(u, np.arange(1, len(u) + 1) / len(u), color=at.PALETTE["blue"], linewidth=2)
    ax.set_xlabel("utilization")
    ax.set_ylabel("share of ASes at or below")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    at.style_axis(ax)
    _save(fig, out, title)


def plot_drops_by_degree(df: pd.DataFrame, out: Path, title: str) -> None:
    drops = df.groupby(degree_class(df["degree"]), observed=False)["errors"].sum()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(drops.index.astype(str), drops.values, color=at.PALETTE["red"], width=0.55)
    for b, v in zip(bars, drops.values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{int(v):,}", ha="center", va="bottom",
                fontsize=8, color=at.PALETTE["ink"])
    ax.set_xlabel("AS degree class")
    ax.set_ylabel("packets dropped (QUEUE-FULL)")
    at.style_axis(ax)
    ax.grid(axis="x", visible=False)
    _save(fig, out, title)


def plot_top_use(use: dict[str, pd.DataFrame], labels: dict[str, str], out: Path, title: str,
                 window: int = 100) -> None:
    """Utilization and waiting packets over time for the busiest ASes."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    colors = [at.PALETTE[c] for c in ("blue", "orange", "aqua", "violet", "magenta")]
    for color, (qid, df) in zip(colors, use.items()):
        axes[0].plot(df["time-step"], df[f"Utilization({window})"], color=color, linewidth=1.6, label=labels[qid])
        axes[1].plot(df["time-step"], df[f"Saturation({window})"], color=color, linewidth=1.6, label=labels[qid])
    axes[0].set_ylabel(f"utilization (mean over {window} steps)")
    axes[0].set_ylim(0, 1.02)
    axes[1].set_ylabel(f"packets waiting (mean over {window} steps)")
    axes[1].set_ylim(bottom=0)
    for ax in axes:
        ax.set_xlabel("time-step")
        at.style_axis(ax)
    axes[0].legend(frameon=False, fontsize=8)
    _save(fig, out, title)


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
def per_queue_table(df: pd.DataFrame, emetrics: pd.DataFrame, asn: dict[str, str], n: int = 20) -> pd.DataFrame:
    """The ``n`` busiest ASes: load, drops and per-visit latency."""
    visits = emetrics.groupby("Queue-sys-id").agg(
        visits=("Job-id", "size"),
        wait_mean=("time-in-queue", "mean"),
        wait_p90=("time-in-queue", lambda s: s.quantile(0.9)),
        latency_mean=("turnaround-time", "mean"),
    )
    rows = []
    for qid in top_queues(df, n):
        r = df.loc[qid]
        v = visits.loc[qid] if qid in visits.index else None
        rows.append({
            "queue": qid,
            "AS": asn[qid],
            "degree": int(r["degree"]),
            "servers": int(r["servers"]),
            "utilization": round(float(r["utilization"]), 3),
            "mean waiting": round(float(r["waiting"]), 2),
            "drops": int(r["errors"]),
            "visits": int(v["visits"]) if v is not None else 0,
            "mean wait": round(float(v["wait_mean"]), 2) if v is not None else float("nan"),
            "p90 wait": round(float(v["wait_p90"]), 2) if v is not None else float("nan"),
            "mean latency per visit": round(float(v["latency_mean"]), 2) if v is not None else float("nan"),
        })
    return pd.DataFrame(rows)


def pick_trace_jobs(emetrics: pd.DataFrame) -> list[str]:
    """Fastest, median and slowest delivered packet by total time spent in ASes."""
    per_job = emetrics.groupby("Job-id")["turnaround-time"].sum().sort_values()
    if per_job.empty:
        return []
    idx = sorted({0, len(per_job) // 2, len(per_job) - 1})
    return [per_job.index[i] for i in idx]


def packets_in(workloads: Sequence[Path]) -> int:
    total = 0
    for p in workloads:
        with open(p, encoding="utf-8") as fh:
            total += sum(1 for _ in fh) - 1
    return total

#!/usr/bin/env python3
"""Analysis helpers used by run_analysis.py (Objective F, SMALL).

These cover the Obj C accessory tools that are not yet on ``main``
(filter-by-queue, filter-by-job, compute-use, plot-use, plot-derive-event-
metrics, create-event-trace) with the same inputs, outputs and definitions as
the design notes in ``src/design/obj-c/``. When those tools land, the driver
can call them instead; the CSV formats here match the design so nothing else
changes.

The Obj C tools that *are* implemented (derive-sys-metrics, plot-sys-metrics,
derive-event-metrics) are invoked by the driver as CLIs, not re-implemented.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Shared chart palette (validated categorical slots + sequential blue ramp).
PALETTE = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "green": "#008300",
    "violet": "#4a3aa7",
    "red": "#e34948",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "ink": "#0b0b0b",
    "muted": "#52514e",
}
BLUE_RAMP = {10: "#86b6ef", 100: "#2a78d6", 1000: "#104281"}  # light -> dark = short -> long window
GROUP_COLORS = {"intake": "#2a78d6", "treatment": "#eb6834", "diagnostics": "#1baf7a", "exit": "#4a3aa7"}
USE_WINDOWS = (10, 100, 1000)
DPI = 110


def style_axis(ax) -> None:
    ax.grid(True, color=PALETTE["grid"], linewidth=1, linestyle="-")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(PALETTE["axis"])
    ax.tick_params(colors=PALETTE["muted"], labelsize=8)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_qmet(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["qid"] = "q" + df["queue-sys-id"].astype(int).astype(str)
    return df


def load_emetrics(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_sysmetrics(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


# --------------------------------------------------------------------------- #
# Filters (design: src/design/obj-c/filters/README.md)
# --------------------------------------------------------------------------- #
def filter_by_queue(qmet: pd.DataFrame, qids: Sequence[str], out: Path) -> pd.DataFrame:
    """filter-by-queue: keep only the given queue ids in qmet.csv."""
    subset = qmet[qmet["qid"].isin(list(qids))].drop(columns=["qid"])
    subset.to_csv(out, index=False)
    return subset


def filter_by_job(events: Path, job_ids: Sequence[str], out: Path) -> int:
    """filter-by-job: keep only event lines whose job id is in job_ids."""
    wanted = set(job_ids)
    kept = 0
    with open(events, encoding="utf-8") as src, open(out, "w", encoding="utf-8", newline="\n") as dst:
        for line in src:
            parts = line.split(maxsplit=2)
            if len(parts) >= 2 and parts[1] in wanted:
                dst.write(line)
                kept += 1
    return kept


# --------------------------------------------------------------------------- #
# USE (design: src/design/obj-c/USE/README.md, PDF p.18-20)
# --------------------------------------------------------------------------- #
def compute_use(
    qmet: pd.DataFrame,
    servers: dict[str, int],
    windows: Iterable[int] = USE_WINDOWS,
) -> dict[str, pd.DataFrame]:
    """compute-use: per queue, sliding-window Utilization / Saturation / Errors.

    Utilization(w) = mean over the last w steps of num-jobs-in-service / servers
    Saturation(w)  = mean over the last w steps of num-jobs-in-queue (waiting)
    Errors(w)      = total num-of-errors over the last w steps
    """
    result: dict[str, pd.DataFrame] = {}
    for qid, group in qmet.groupby("qid", sort=False):
        g = group.sort_values("time-step").reset_index(drop=True)
        out = pd.DataFrame({"time-step": g["time-step"]})
        util = g["num-jobs-in-service"] / servers[qid]
        for w in windows:
            out[f"Utilization({w})"] = util.rolling(w, min_periods=1).mean().round(4)
            out[f"Saturation({w})"] = g["num-jobs-in-queue"].rolling(w, min_periods=1).mean().round(3)
            out[f"Errors({w})"] = g["num-of-errors"].rolling(w, min_periods=1).sum().astype(int)
        result[qid] = out
    return result


def write_use(use: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for qid, df in use.items():
        df.to_csv(out_dir / f"quse-{qid}.csv", index=False)


def plot_use(
    use: dict[str, pd.DataFrame],
    metric: str,
    names: dict[str, str],
    out: Path,
    title: str,
    ylabel: str,
    windows: Iterable[int] = USE_WINDOWS,
    ylim: tuple[float, float] | None = None,
) -> None:
    """plot-use: small multiples, one panel per queue, one shade per window."""
    qids = list(use)
    ncols = 4
    nrows = int(np.ceil(len(qids) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 2.6 * nrows + 0.8), sharex=True, sharey=True)
    axes = np.atleast_2d(axes)
    for i, qid in enumerate(qids):
        ax = axes[i // ncols][i % ncols]
        df = use[qid]
        for w in windows:
            ax.plot(df["time-step"], df[f"{metric}({w})"], color=BLUE_RAMP[w], linewidth=1.6 if w != 10 else 0.8,
                    alpha=1.0 if w != 10 else 0.6, label=f"window {w}")
        ax.set_title(f"{qid} {names.get(qid, '')}", loc="left", fontsize=9, color=PALETTE["ink"])
        style_axis(ax)
        if ylim:
            ax.set_ylim(*ylim)
    for j in range(len(qids), nrows * ncols):
        axes[j // ncols][j % ncols].set_visible(False)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=3, frameon=False, fontsize=9)
    fig.supxlabel("time-step (10 min)", fontsize=9, color=PALETTE["ink"])
    fig.supylabel(ylabel, fontsize=9, color=PALETTE["ink"])
    fig.suptitle(title, x=0.01, ha="left", color=PALETTE["ink"])
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Event-metric plots (design: src/design/obj-c/events/plot-emetrics.pseudo, PDF p.24)
# --------------------------------------------------------------------------- #
def plot_emetrics_scatter(emetrics: pd.DataFrame, names: dict[str, str], out: Path, title: str,
                          y: str = "response-time") -> None:
    """plot-derive-event-metrics --scat="arrival-time,<y>": one panel per queue."""
    qids = sorted(emetrics["Queue-sys-id"].unique(), key=lambda q: int(q[1:]))
    ncols = 4
    nrows = int(np.ceil(len(qids) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 2.6 * nrows + 0.8), sharex=True)
    axes = np.atleast_2d(axes)
    for i, qid in enumerate(qids):
        ax = axes[i // ncols][i % ncols]
        g = emetrics[emetrics["Queue-sys-id"] == qid]
        ax.scatter(g["arrival-time"], g[y], s=6, color=PALETTE["blue"], alpha=0.45, linewidths=0)
        ax.set_title(f"{qid} {names.get(qid, '')}  (n={len(g)})", loc="left", fontsize=9, color=PALETTE["ink"])
        style_axis(ax)
        ax.set_ylim(bottom=0)
    for j in range(len(qids), nrows * ncols):
        axes[j // ncols][j % ncols].set_visible(False)
    fig.supxlabel("arrival-time in queue (time-step)", fontsize=9, color=PALETTE["ink"])
    fig.supylabel(f"{y} (time steps)", fontsize=9, color=PALETTE["ink"])
    fig.suptitle(title, x=0.01, ha="left", color=PALETTE["ink"])
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def plot_emetrics_hist(emetrics: pd.DataFrame, names: dict[str, str], out: Path, title: str,
                       column: str = "arrival-time", bins: int = 50) -> None:
    """plot-derive-event-metrics --hist=<column>: one panel per queue."""
    qids = sorted(emetrics["Queue-sys-id"].unique(), key=lambda q: int(q[1:]))
    ncols = 4
    nrows = int(np.ceil(len(qids) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 2.6 * nrows + 0.8), sharex=True)
    axes = np.atleast_2d(axes)
    for i, qid in enumerate(qids):
        ax = axes[i // ncols][i % ncols]
        g = emetrics[emetrics["Queue-sys-id"] == qid]
        ax.hist(g[column], bins=bins, color=PALETTE["blue"], alpha=0.9, linewidth=0)
        ax.set_title(f"{qid} {names.get(qid, '')}  (n={len(g)})", loc="left", fontsize=9, color=PALETTE["ink"])
        style_axis(ax)
    for j in range(len(qids), nrows * ncols):
        axes[j // ncols][j % ncols].set_visible(False)
    fig.supxlabel(column, fontsize=9, color=PALETTE["ink"])
    fig.supylabel("visits", fontsize=9, color=PALETTE["ink"])
    fig.suptitle(title, x=0.01, ha="left", color=PALETTE["ink"])
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Event trace (design: src/design/obj-c/events/create-etrace.pseudo, PDF p.25)
# --------------------------------------------------------------------------- #
@dataclass
class TraceEvent:
    time: int
    job: str
    qsid: str
    kind: str
    rest: str


def read_events(path: Path, job_ids: set[str] | None = None) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split(maxsplit=5)
            if len(parts) < 5 or parts[2] != "IN":
                continue
            if job_ids is not None and parts[1] not in job_ids:
                continue
            events.append(TraceEvent(int(parts[0]), parts[1], parts[3], parts[4], parts[5].strip() if len(parts) > 5 else ""))
    return events


def create_etrace(events_path: Path, job_ids: Sequence[str], groups: dict[str, str], names: dict[str, str],
                  out: Path, title: str) -> None:
    """create-event-trace: one lifeline per job; box = waiting, circle = in service, x = error.

    Color encodes the stage group of the queue the patient is in (intake /
    treatment / diagnostics / exit); the queue id is written on each service
    segment so the exact station is never color-alone.
    """
    events = read_events(events_path, set(job_ids))
    by_job: dict[str, list[TraceEvent]] = {}
    for ev in events:
        by_job.setdefault(ev.job, []).append(ev)

    # Journeys are aligned at each patient's own arrival so they can be compared
    # side by side; the y label carries the absolute arrival time.
    spans = [max(e.time for e in evs) - min(e.time for e in evs) for evs in by_job.values() if evs]
    label_min = max(1.0, 0.03 * max(spans)) if spans else 1.0

    fig, ax = plt.subplots(figsize=(13, 0.6 * len(job_ids) + 1.8))
    yticks, ylabels = [], []
    seen_groups: set[str] = set()
    for y, job in enumerate(job_ids):
        evs = sorted(by_job.get(job, []), key=lambda e: e.time)
        if not evs:
            continue
        t0 = evs[0].time
        span = evs[-1].time - t0
        yticks.append(y)
        ylabels.append(f"{job}  (t={t0}, {span} steps)")
        ax.plot([0, span], [y, y], color=PALETTE["axis"], linewidth=1, zorder=1)
        arrive: dict[str, int] = {}
        enter: dict[str, int] = {}
        for ev in evs:
            x = ev.time - t0
            color = GROUP_COLORS.get(groups.get(ev.qsid, ""), PALETTE["muted"])
            seen_groups.add(groups.get(ev.qsid, ""))
            if ev.kind == "ARRIVE-VIA":
                arrive[ev.qsid] = x
                ax.scatter([x], [y], marker="s", s=30, facecolors="white", edgecolors=color, linewidths=1.5, zorder=4)
            elif ev.kind == "ENTERS-SERVER":
                enter[ev.qsid] = x
                if ev.qsid in arrive and x > arrive[ev.qsid]:
                    # waiting segment: light wash from arrival to service start
                    ax.plot([arrive[ev.qsid], x], [y, y], color=color, linewidth=7, alpha=0.25, zorder=2,
                            solid_capstyle="butt")
            elif ev.kind == "EXITS-SERVER":
                start = enter.get(ev.qsid, x)
                ax.plot([start, x], [y, y], color=color, linewidth=7, zorder=3, solid_capstyle="butt")
                ax.scatter([start], [y], marker="o", s=22, color=color, edgecolors="white", linewidths=1, zorder=4)
                if x - start >= label_min:
                    ax.text((start + x) / 2, y + 0.24, ev.qsid, ha="center", va="bottom", fontsize=7,
                            color=PALETTE["muted"])
            elif ev.kind == "ERROR":
                ax.scatter([x], [y], marker="x", s=70, color=PALETTE["red"], linewidths=2, zorder=5)
                ax.text(x, y + 0.24, f"{ev.qsid} {ev.rest}", ha="left", va="bottom", fontsize=7, color=PALETTE["red"])
            elif ev.kind == "DEPART-VIA" and ev.rest not in groups:
                ax.scatter([x], [y], marker="*", s=100, color=PALETTE["ink"], zorder=5)

    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.set_xlabel("time since the patient arrived (10-min steps)")
    ax.set_xlim(left=-0.5)
    ax.set_title(title, loc="left", color=PALETTE["ink"])
    style_axis(ax)
    ax.grid(axis="y", visible=False)
    from matplotlib.lines import Line2D

    handles = [Line2D([0], [0], color=GROUP_COLORS[g], linewidth=6, label=f"{g} (in service)") for g in
               ("intake", "treatment", "diagnostics", "exit") if g in seen_groups]
    handles += [
        Line2D([0], [0], marker="s", color="white", markeredgecolor=PALETTE["muted"], markersize=7, linewidth=0,
               label="arrive / waiting"),
        Line2D([0], [0], marker="o", color=PALETTE["muted"], markersize=6, linewidth=0, label="enters server"),
        Line2D([0], [0], marker="*", color=PALETTE["ink"], markersize=10, linewidth=0, label="leaves ED (sink)"),
        Line2D([0], [0], marker="x", color=PALETTE["red"], markersize=7, linewidth=0, label="error"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #
def per_queue_summary(
    qmet: pd.DataFrame,
    emetrics: pd.DataFrame,
    servers: dict[str, int],
    names: dict[str, str],
    steady: tuple[int, int],
) -> pd.DataFrame:
    """Per-station table: utilization, saturation, errors, waits, Little's law check.

    Little's law: L = lambda * W, with L the time-average number of patients at
    the station (waiting + in service), lambda the visit rate, W the mean
    turnaround per visit. Both sides are measured over the steady window.
    """
    lo, hi = steady
    rows = []
    for qid, g in qmet.groupby("qid", sort=False):
        s = g[(g["time-step"] >= lo) & (g["time-step"] < hi)]
        if s.empty:
            s = g
        horizon = max(1, len(s))
        visits = emetrics[(emetrics["Queue-sys-id"] == qid) & (emetrics["arrival-time"] >= lo)
                          & (emetrics["arrival-time"] < hi)]
        n_visits = len(visits)
        lam = n_visits / horizon
        w_turn = float(visits["turnaround-time"].mean()) if n_visits else float("nan")
        w_wait = float(visits["time-in-queue"].mean()) if n_visits else float("nan")
        p90_wait = float(visits["time-in-queue"].quantile(0.9)) if n_visits else float("nan")
        L = float((s["num-jobs-in-queue"] + s["num-jobs-in-service"]).mean())
        rows.append({
            "queue": qid,
            "station": names.get(qid, qid),
            "servers": servers[qid],
            "utilization": round(float(s["num-jobs-in-service"].mean() / servers[qid]), 3),
            "saturation(mean waiting)": round(float(s["num-jobs-in-queue"].mean()), 2),
            "errors(total run)": int(g["num-of-errors"].sum()),
            "visits": n_visits,
            "mean wait": round(w_wait, 2),
            "p90 wait": round(p90_wait, 2),
            "mean turnaround": round(w_turn, 2),
            "L (measured)": round(L, 2),
            "lambda*W": round(lam * w_turn, 2) if n_visits else float("nan"),
        })
    return pd.DataFrame(rows)


def df_to_markdown(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                cells.append("" if np.isnan(v) else format(v, floatfmt))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_csv_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

"""MEDIUM validation, queue summaries, and USE plots.

Shared Objective A/C/E tools provide plots, filters, and derived CSVs
through implementation_tools.py. The event reconstruction here independently
checks graph-specific routing, service duration, and conservation.
"""

from __future__ import annotations

import csv
import gzip
from collections import Counter
import os
import tempfile
from pathlib import Path
from typing import Iterable

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "objf-matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from implementation_tools import create_outputs

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
BLUE_RAMP = {
    10: "#86b6ef",
    100: "#2a78d6",
    1000: "#104281",
}  # light -> dark = short -> long window
USE_WINDOWS = (10, 100, 1000)
DPI = 110


def style_axis(ax) -> None:
    """Apply the shared plot style."""
    ax.grid(True, color=PALETTE["grid"], linewidth=1, linestyle="-")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(PALETTE["axis"])
    ax.tick_params(colors=PALETTE["muted"], labelsize=8)


# --------------------------------------------------------------------------- #
# Shared tools are called through implementation_tools.py
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# USE (design: src/design/obj-c/USE/README.md, PDF p.18-20)
# --------------------------------------------------------------------------- #
def compute_use(
    queue_metrics: pd.DataFrame,
    servers: dict[str, int],
    windows: Iterable[int] = USE_WINDOWS,
) -> dict[str, pd.DataFrame]:
    """compute-use: per queue, sliding-window Utilization / Saturation / Errors.

    Utilization(w) = mean over the last w steps of num-jobs-in-service / servers
    Saturation(w)  = mean over the last w steps of num-jobs-in-queue (waiting)
    Errors(w)      = mean errors per tick over the available window
    """
    result: dict[str, pd.DataFrame] = {}
    for queue_name, group in queue_metrics.groupby("qid", sort=False):
        queue_data = group.sort_values("time-step").reset_index(drop=True)
        output = pd.DataFrame({"time-step": queue_data["time-step"]})
        util = queue_data["num-jobs-in-service"] / servers[queue_name]
        for w in windows:
            output[f"Utilization({w})"] = util.rolling(w, min_periods=1).mean().round(4)
            output[f"Saturation({w})"] = (
                queue_data["num-jobs-in-queue"]
                .rolling(w, min_periods=1)
                .mean()
                .round(3)
            )
            output[f"Errors({w})"] = (
                queue_data["num-of-errors"].rolling(w, min_periods=1).mean()
            )
        result[queue_name] = output
    return result


def plot_use(
    use: dict[str, pd.DataFrame],
    metric: str,
    names: dict[str, str],
    output: Path,
    title: str,
    ylabel: str,
    windows: Iterable[int] = USE_WINDOWS,
    ylim: tuple[float, float] | None = None,
) -> None:
    """plot-use: small multiples, one panel per queue, one shade per window."""
    qids = list(use)
    ncols = 4
    nrows = int(np.ceil(len(qids) / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(14, 2.6 * nrows + 0.8), sharex=True, sharey=True
    )
    axes = np.atleast_2d(axes)
    for i, queue_name in enumerate(qids):
        ax = axes[i // ncols][i % ncols]
        df = use[queue_name]
        for w in windows:
            ax.plot(
                df["time-step"],
                df[f"{metric}({w})"],
                color=BLUE_RAMP[w],
                linewidth=1.6 if w != 10 else 0.8,
                alpha=1.0 if w != 10 else 0.6,
                label=f"window {w}",
            )
        ax.set_title(
            f"{queue_name} {names.get(queue_name, '')}",
            loc="left",
            fontsize=9,
            color=PALETTE["ink"],
        )
        style_axis(ax)
        if ylim:
            ax.set_ylim(*ylim)
    for job_id in range(len(qids), nrows * ncols):
        axes[job_id // ncols][job_id % ncols].set_visible(False)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=3, frameon=False, fontsize=9)
    fig.supxlabel("time (ticks)", fontsize=9, color=PALETTE["ink"])
    fig.supylabel(ylabel, fontsize=9, color=PALETTE["ink"])
    fig.suptitle(title, x=0.01, ha="left", color=PALETTE["ink"])
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output, dpi=DPI)
    plt.close(fig)


# MEDIUM derivation and conservation checks. These operate on raw engine outputs.


def text_open(path):
    """Open either a plain-text file or a gzip-compressed text file."""
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)


def derive_and_validate(events, jobs, graph, routes, counts, depth, queue_metrics):
    """Reconstruct visits and job outcomes, then check routing and conservation."""
    manifest = jobs.set_index("job").to_dict("index")
    active = {}
    pending = {}
    terminal = {}
    seen = set()
    visits = []
    routing_counts = Counter()
    transfers = 0
    with text_open(events) as f:
        for line in f:
            time_step, job_id, _, queue_name, kind, rest = line.rstrip().split(
                maxsplit=5
            )
            time_step = int(time_step)
            queue_id = int(queue_name[1:])
            assert queue_id in graph and job_id in manifest and job_id not in terminal
            if kind == "ARRIVE-VIA":
                assert job_id not in active
                if rest.startswith("q"):
                    old, dest, depart = pending.pop(job_id)
                    assert (
                        rest == f"q{old}"
                        and dest == queue_id
                        and time_step == depart + 1
                        and graph.has_edge(old, queue_id)
                    )
                else:
                    assert job_id not in seen and manifest[job_id] == dict(
                        arrival=time_step, source=queue_id
                    )
                    seen.add(job_id)
                active[job_id] = dict(job=job_id, queue=queue_id, arrival=time_step)
            elif kind == "ENTERS-SERVER":
                assert (
                    active[job_id]["queue"] == queue_id
                    and 0 <= int(rest) < counts[queue_id]
                )
                active[job_id]["start"] = time_step
            elif kind == "EXITS-SERVER":
                visit = active.pop(job_id)
                assert visit["queue"] == queue_id
                visit.update(
                    end=time_step,
                    wait=visit["start"] - visit["arrival"],
                    service=time_step - visit["start"],
                )
                assert visit["wait"] >= 0 and visit["service"] == 2
                visits.append(visit)
            elif kind == "DEPART-VIA":
                if rest.startswith("q"):
                    dest = int(rest[1:])
                    assert (
                        dest
                        == routes[queue_id][
                            routing_counts[queue_id] % len(routes[queue_id])
                        ]
                    )
                    routing_counts[queue_id] += 1
                    transfers += 1
                    pending[job_id] = (queue_id, dest, time_step)
                else:
                    assert rest == f"out{queue_id}.wl"
                    terminal[job_id] = (time_step, "completed")
            elif kind == "ERROR":
                assert rest == "QUEUE-FULL"
                visit = active.pop(job_id)
                assert "start" not in visit and visit["arrival"] == time_step
                terminal[job_id] = (time_step, "dropped")
    assert (
        not active and not pending and seen == set(manifest) and set(terminal) == seen
    )
    visit_metrics = pd.DataFrame(visits)
    job_metrics = pd.DataFrame(
        [
            dict(
                job=job_id,
                arrival=manifest[job_id]["arrival"],
                departure=time_step,
                status=status,
                latency=time_step - manifest[job_id]["arrival"],
            )
            for job_id, (time_step, status) in terminal.items()
        ]
    )
    completed = job_metrics[job_metrics.status == "completed"]
    grouped = visit_metrics.groupby("job").agg(
        n=("queue", "size"), wait=("wait", "sum")
    )
    for r in completed.itertuples():
        assert (
            grouped.loc[r.job, "n"] == 4
            and r.latency == grouped.loc[r.job, "wait"] + 11
        )
    end = int(queue_metrics["time-step"].max())
    horizon = end + 1
    assert (
        len(queue_metrics) == len(graph) * horizon
        and not queue_metrics.duplicated(["time-step", "queue-sys-id"]).any()
    )
    assert queue_metrics["num-jobs-in-queue"].between(0, depth).all()
    assert (
        queue_metrics["num-jobs-in-service"]
        <= queue_metrics["queue-sys-id"].map(counts)
    ).all()
    assert (queue_metrics[["num-jobs-in-service", "num-of-errors"]] >= 0).all().all()
    assert (
        queue_metrics[queue_metrics["time-step"] == end][
            ["num-jobs-in-queue", "num-jobs-in-service"]
        ]
        .sum()
        .sum()
        == 0
    )
    assert (
        int(queue_metrics["num-of-errors"].sum())
        == (job_metrics.status == "dropped").sum()
    )
    aggregate = queue_metrics.groupby("queue-sys-id")[
        ["num-jobs-in-queue", "num-jobs-in-service"]
    ].sum()
    event_aggregate = (
        visit_metrics.groupby("queue")[["wait", "service"]]
        .sum()
        .reindex(aggregate.index, fill_value=0)
    )
    assert np.array_equal(aggregate.values, event_aggregate.values)
    area = int(aggregate.sum().sum()) + transfers
    assert area == int(job_metrics.latency.sum())
    # Check every completion sink against the terminal events.
    sinks = []
    for p in events.parent.glob("out*.wl"):
        with p.open() as f:
            sinks.extend(list(csv.DictReader(f)))
    assert len(sinks) == len(completed) and {r["Job Id"] for r in sinks} == set(
        completed.job
    )
    assert all(
        r["Tasks"] == "[]" and int(r["arrival time"]) == terminal[r["Job Id"]][0]
        for r in sinks
    )
    return visit_metrics, job_metrics


def markdown(df):
    """Format a DataFrame as a readable Markdown table."""
    lines = [
        "| " + " | ".join(map(str, df.columns)) + " |",
        "|" + "|".join("---" for _ in df.columns) + "|",
    ]
    for row in df.itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row)
            + " |"
        )
    return "\n".join(lines)


def summarize_queues(
    queue_metrics, visits, counts, horizon, interior_start, interior_end
):
    """Summarize each queue and check full-run Little's law."""
    table = queue_metrics.groupby("queue-sys-id").agg(
        mean_waiting=("num-jobs-in-queue", "mean"),
        busy=("num-jobs-in-service", "mean"),
        errors=("num-of-errors", "sum"),
        peak_waiting=("num-jobs-in-queue", "max"),
    )
    table["servers"] = pd.Series(counts)
    table["utilization"] = table.busy / table.servers
    interior = queue_metrics[
        queue_metrics["time-step"].between(interior_start, interior_end - 1)
    ].groupby("queue-sys-id")
    table["interior_utilization"] = (
        interior["num-jobs-in-service"].mean() / table.servers
    )
    table["interior_mean_waiting"] = interior["num-jobs-in-queue"].mean()
    visit_summary = visits.groupby("queue").agg(
        visits=("job", "size"),
        mean_wait=("wait", "mean"),
        p90_wait=("wait", lambda x: x.quantile(0.9)),
    )
    visit_summary["mean_turnaround"] = (
        visits.assign(turn=visits.end - visits.arrival).groupby("queue").turn.mean()
    )
    table = table.join(visit_summary)
    table["L"] = table.mean_waiting + table.busy
    table["lambda_W"] = table.visits / horizon * table.mean_turnaround
    assert np.allclose(table.L, table.lambda_W.fillna(0))
    table.index.name = "queue"
    table = table.reset_index()
    return table


def dashboard(
    scenario, run_dir, result_dir, jobs, graph, routes, counts, queue_metrics, events
):
    """Validate one scenario, save derived metrics, and create its dashboard."""
    result_dir.mkdir(parents=True, exist_ok=True)
    visits, job_metrics = derive_and_validate(
        events, jobs, graph, routes, counts, scenario.depth, queue_metrics
    )
    job_metrics.to_csv(run_dir / "jobs.csv.gz", index=False)
    completed = job_metrics[job_metrics.status == "completed"]
    horizon = int(queue_metrics["time-step"].max()) + 1
    last_arrival = int(jobs.arrival.max())
    interior_start = int(0.1 * last_arrival)
    interior_end = max(interior_start + 1, int(0.9 * last_arrival))
    table = summarize_queues(
        queue_metrics, visits, counts, horizon, interior_start, interior_end
    )
    table.to_csv(result_dir / "per-queue.csv", index=False)
    busiest_nodes = (
        table.sort_values(["mean_waiting", "queue"], ascending=[False, True])
        .head(12)["queue"]
        .tolist()
    )
    names = {f"q{n}": f"node {n}" for n in graph}
    servers = {f"q{n}": v for n, v in counts.items()}
    selected = {}
    first = True
    # Full all-node USE artifact, bounded memory; dashboards show top-12 waiting nodes.
    with gzip.open(run_dir / "quse.csv.gz", "wt") as output:
        for queue_id, queue_data in queue_metrics.groupby("queue-sys-id", sort=True):
            queue_name = f"q{queue_id}"
            local = queue_data.copy()
            local["qid"] = queue_name
            use = compute_use(local, servers)[queue_name]
            use.insert(1, "queue", queue_id)
            use.to_csv(output, index=False, header=first, float_format="%.6g")
            first = False
            if queue_id in busiest_nodes:
                selected[queue_name] = use
    selected = {f"q{queue_id}": selected[f"q{queue_id}"] for queue_id in busiest_nodes}
    for metric, label, suffix in [
        ("Utilization", "busy servers / servers", "utilization"),
        ("Saturation", "waiting requests", "saturation"),
        ("Errors", "drops per tick in window", "errors"),
    ]:
        plot_use(
            selected,
            metric,
            names,
            result_dir / f"use-{suffix}.png",
            f"{scenario.name}: {metric}, top 12 nodes by full-run mean waiting",
            label,
            ylim=(0, 1.02) if metric == "Utilization" else None,
        )
    create_outputs(
        scenario,
        run_dir,
        result_dir,
        events,
        visits,
        job_metrics,
        queue_metrics,
        jobs,
        busiest_nodes,
    )
    dropped = job_metrics[job_metrics.status == "dropped"]
    if scenario.name == "base-30k":
        heat = (
            queue_metrics.assign(bin=queue_metrics["time-step"] // 20)
            .groupby(["queue-sys-id", "bin"])["num-jobs-in-queue"]
            .mean()
            .unstack()
        )
        fig, ax = plt.subplots(figsize=(11, 6))
        im = ax.imshow(
            np.log1p(heat),
            aspect="auto",
            origin="lower",
            extent=[0, horizon, 0, len(graph)],
            cmap="magma",
        )
        ax.set(
            xlabel="Time (ticks)",
            ylabel="Node rank (sorted original ID)",
            title="All 803 nodes: log(1 + mean waiting), 20-tick bins",
        )
        fig.colorbar(im, ax=ax, label="log(1 + waiting)")
        fig.tight_layout()
        fig.savefig(result_dir / "all-queues.png", dpi=DPI)
        plt.close(fig)
    summary = dict(
        scenario=scenario.name,
        study=scenario.study,
        seed=scenario.seed,
        jobs=scenario.jobs,
        load=scenario.load,
        requested_resource_change_pct=100 * (scenario.resource - 1),
        total_servers=sum(counts.values()),
        actual_resource_change_pct=100 * (sum(counts.values()) / (2 * len(graph)) - 1),
        completed=len(completed),
        dropped=len(dropped),
        drop_pct=100 * len(dropped) / len(job_metrics),
        horizon=horizon,
        last_arrival=last_arrival,
        drain_ticks=horizon - 1 - last_arrival,
        throughput=len(completed) / horizon,
        latency_mean=completed.latency.mean(),
        latency_median=completed.latency.median(),
        latency_p90=completed.latency.quantile(0.9),
        max_utilization=table.utilization.max(),
        max_mean_waiting=table.mean_waiting.max(),
        peak_waiting=int(table.peak_waiting.max()),
        interior_start=interior_start,
        interior_end_exclusive=interior_end,
    )
    pd.DataFrame([summary]).to_csv(result_dir / "summary.csv", index=False)
    return summary

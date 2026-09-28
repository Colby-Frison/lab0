#!/usr/bin/env python3
"""Objective F (SMALL) driver: emergency-department queueing network.

Reproduces every artifact under this directory:

    workloads/   Obj A generator output (patient streams)
    configs/     one qconf.csv (+ station table) per scenario
    runs/        simulator output per scenario (qmet.csv, events.log, sinks) -- git-ignored
    results/     plots and summary tables per scenario + cross-scenario comparisons

Pipeline per scenario:
    workload_generator.py  ->  simple-queue-sim  ->  derive-sys-metrics / plot-sys-metrics
                                                  ->  derive-event-metrics
                                                  ->  USE, filters, event-metric plots, event trace
                                                      (analysis_tools.py stand-ins for the Obj C
                                                       tools not yet on main)

Usage:
    python run_analysis.py                  # all scenarios
    python run_analysis.py --scenarios base-3k,srv+50
    python run_analysis.py --skip-sim       # re-run analysis on existing runs/
    python run_analysis.py --list
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import analysis_tools as at
import ed_model as ed

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GEN = REPO / "src/implementation/obj-a/workload-generator/workload_generator.py"
OBJC = REPO / "src/implementation/obj-c"
DERIVE_SYS = OBJC / "derive-sys-metrics/derive_sys_metrics.py"
PLOT_SYS = OBJC / "plot-sys-metrics/plot_sys_metrics.py"
DERIVE_EVT = OBJC / "derive-event-metrics/derive_event_metrics.py"
SIM_CANDIDATES = [
    REPO / "src/implementation/obj-b/simple-queue-sim/build/simple-queue-sim.exe",
    REPO / "src/implementation/obj-b/simple-queue-sim/build/simple-queue-sim",
    REPO / "src/implementation/obj-e/multi-queue-sim/build/multi-queue-sim.exe",
    REPO / "src/implementation/obj-e/multi-queue-sim/build/multi-queue-sim",
]
BASE_LAMBDA = 2.0  # patients per 10-minute step in the generated stream
PY = sys.executable


def log(msg: str) -> None:
    print(f"[obj-f] {msg}", flush=True)


def run(cmd: list[str], cwd: Path, capture_to: Path | None = None) -> str:
    """Run a CLI; return its stderr (the Obj C tools report drop counts there)."""
    proc = subprocess.run([str(c) for c in cmd], cwd=str(cwd), text=True, capture_output=True)
    if capture_to is not None:
        with open(capture_to, "a", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(str(c) for c in cmd) + "\n")
            fh.write(proc.stdout)
            fh.write(proc.stderr)
            fh.write("\n")
    if proc.returncode != 0:
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(str(c) for c in cmd)}\n{proc.stderr}")
    return proc.stderr


def find_sim(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        raise SystemExit(f"--sim not found: {explicit}")
    for c in SIM_CANDIDATES:
        if c.exists():
            return c
    raise SystemExit(
        "simulator binary not found. Build it first:\n"
        "  cd src/implementation/obj-b/simple-queue-sim && cmake -S . -B build && cmake --build build"
    )


# --------------------------------------------------------------------------- #
# Workloads
# --------------------------------------------------------------------------- #
def ensure_workload(sc: ed.Scenario) -> Path:
    wl_dir = HERE / "workloads"
    wl_dir.mkdir(exist_ok=True)
    tag = sc.interval.replace(":", "-")
    base = wl_dir / f"arrivals-{tag}.wl"
    if not base.exists():
        log(f"generate workload {base.name} (poisson lambda={BASE_LAMBDA}, seed={sc.seed})")
        run([PY, GEN, "--interval", sc.interval, "--dist", "poisson", "--lam", str(BASE_LAMBDA),
             "--seed", str(sc.seed), "--out", base], cwd=HERE)
    if sc.rate_factor == 1.0:
        return base
    scaled = wl_dir / f"arrivals-{tag}-x{sc.rate_factor:g}.wl"
    if not scaled.exists():
        # factor 1.5 load = arrival times x (1/1.5); factor 0.5 load = arrival times x 2
        n = ed.rescale_arrivals(base, scaled, 1.0 / sc.rate_factor)
        log(f"rescaled {n} arrivals -> {scaled.name} (load x{sc.rate_factor:g})")
    return scaled


def count_jobs(workload: Path) -> int:
    with open(workload, encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


def horizon_of(sc: ed.Scenario) -> int:
    end = int(sc.interval.split(":")[1])
    return int(end / sc.rate_factor)


# --------------------------------------------------------------------------- #
# Per-scenario pipeline
# --------------------------------------------------------------------------- #
def job_los(events: Path, queue_ids: set[str]) -> tuple[dict[str, tuple[int, int]], set[str]]:
    """Per-job (source arrival, sink departure) plus the set of dropped jobs."""
    arrivals: dict[str, int] = {}
    finished: dict[str, tuple[int, int]] = {}
    dropped: set[str] = set()
    with open(events, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split(maxsplit=5)
            if len(parts) < 5:
                continue
            t, job, kind = int(parts[0]), parts[1], parts[4]
            edge = parts[5].strip() if len(parts) > 5 else ""
            if kind == "ARRIVE-VIA" and edge not in queue_ids:
                arrivals[job] = t
            elif kind == "DEPART-VIA" and edge not in queue_ids and job in arrivals:
                finished[job] = (arrivals[job], t)
            elif kind == "ERROR" and edge.startswith("QUEUE-FULL"):
                dropped.add(job)
    return finished, dropped


def pick_trace_jobs(finished: dict[str, tuple[int, int]], dropped: set[str], steady: tuple[int, int]) -> list[str]:
    lo, hi = steady
    rows = [(j, a, d - a) for j, (a, d) in finished.items() if lo <= a < hi]
    if not rows:
        rows = [(j, a, d - a) for j, (a, d) in finished.items()]
    rows.sort(key=lambda r: r[2])
    n = len(rows)
    picks: list[str] = []
    if n:
        idx = sorted({0, 1, n // 2 - 1, n // 2, n // 2 + 1, int(n * 0.9), int(n * 0.97), n - 1})
        picks = [rows[i][0] for i in idx if 0 <= i < n]
    for j in sorted(dropped, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
        if j not in picks:
            picks.append(j)
            break
    return picks[:10]


def analyze_scenario(sc: ed.Scenario, sim: Path, skip_sim: bool) -> dict:
    run_dir = HERE / "runs" / sc.name
    res_dir = HERE / "results" / sc.name
    cfg_dir = HERE / "configs"
    run_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.mkdir(exist_ok=True)
    tool_log = run_dir / "tool-log.txt"
    if tool_log.exists():
        tool_log.unlink()

    workload = ensure_workload(sc)
    stations = sc.stations
    names = {s.id: s.name for s in stations}
    groups = {s.id: s.group for s in stations}
    servers = {s.id: s.servers for s in stations}
    config = cfg_dir / f"{sc.name}.csv"
    ed.write_config(stations, config, workload.relative_to(HERE), run_dir.relative_to(HERE))
    ed.write_station_table(stations, cfg_dir / f"{sc.name}.md")

    qmet_path, events_path = run_dir / "qmet.csv", run_dir / "events.log"
    horizon = horizon_of(sc)
    if not skip_sim or not events_path.exists():
        t0 = time.time()
        run([sim, "--config", config.relative_to(HERE), "--limit", str(horizon * 6),
             "--qmet", qmet_path.relative_to(HERE), "--events", events_path.relative_to(HERE)],
            cwd=HERE, capture_to=tool_log)
        log(f"{sc.name}: simulated in {time.time() - t0:.1f}s")

    # --- Obj C tools (CLI) ------------------------------------------------- #
    sys_csv = run_dir / "sysmetrics.csv"
    sys_all = run_dir / "sysmetrics-overall.csv"
    emet_csv = run_dir / "emetrics.csv"
    run([PY, DERIVE_SYS, "--events", events_path, "--out", sys_csv, "--window", "10", "--dense", "-v"],
        cwd=HERE, capture_to=tool_log)
    run([PY, DERIVE_SYS, "--events", events_path, "--out", sys_all, "--window", "100000000"],
        cwd=HERE, capture_to=tool_log)
    run([PY, PLOT_SYS, "--sysmetrics", sys_csv, "--out", res_dir / "resplot.png",
         "--title", f"{sc.title}: end-to-end length of stay (10-step windows)"], cwd=HERE, capture_to=tool_log)
    run([PY, DERIVE_EVT, "--events", events_path, "--out", emet_csv, "-v"], cwd=HERE, capture_to=tool_log)

    # --- stand-ins for the remaining Obj C tools ---------------------------- #
    qmet = at.load_qmet(qmet_path)
    emetrics = at.load_emetrics(emet_csv)
    steady = (int(horizon * 0.1), int(horizon * 0.9))

    use = at.compute_use(qmet, servers)
    at.write_use(use, run_dir / "use")
    at.plot_use(use, "Utilization", names, res_dir / "use-utilization.png",
                f"{sc.title}: utilization (busy servers / servers)", "utilization", ylim=(0, 1.02))
    at.plot_use(use, "Saturation", names, res_dir / "use-saturation.png",
                f"{sc.title}: saturation (patients waiting)", "patients waiting")
    at.plot_use(use, "Errors", names, res_dir / "use-errors.png",
                f"{sc.title}: errors (patients turned away, QUEUE-FULL)", "errors in window")

    if sc.extra_plots:
        at.plot_emetrics_scatter(emetrics, names, res_dir / "emetrics-scatter.png",
                                 f"{sc.title}: waiting time per visit vs arrival time")
        at.plot_emetrics_hist(emetrics, names, res_dir / "emetrics-hist.png",
                              f"{sc.title}: visits per queue over time (arrival-time histogram)")
        at.plot_emetrics_scatter(emetrics, names, res_dir / "emetrics-scatter-turnaround.png",
                                 f"{sc.title}: turnaround per visit vs arrival time", y="turnaround-time")

    finished, dropped = job_los(events_path, set(names))
    trace_jobs = pick_trace_jobs(finished, dropped, steady)
    if trace_jobs:
        at.filter_by_job(events_path, trace_jobs, run_dir / "trace-jobs.log")
        at.create_etrace(events_path, trace_jobs, groups, names, res_dir / "etrace.png",
                         f"{sc.title}: patient journeys (fastest, typical, slowest, and a turned-away patient)")
        if sc.extra_plots:
            shutil.copy(run_dir / "trace-jobs.log", res_dir / "trace-jobs.log")
    hot = "q5" if "q5" in servers else next(iter(servers))
    at.filter_by_queue(qmet, [hot], run_dir / f"{hot}_metrics.csv")

    # --- summary ------------------------------------------------------------ #
    table = at.per_queue_summary(qmet, emetrics, servers, names, steady)
    table.to_csv(res_dir / "per-queue.csv", index=False)
    (res_dir / "per-queue.md").write_text(at.df_to_markdown(table) + "\n", encoding="utf-8")

    overall = pd.read_csv(sys_all)
    o = overall.iloc[0] if len(overall) else None
    patients = count_jobs(workload)
    completed = int(overall["throughput"].sum()) if len(overall) else 0
    total_drops = int(qmet["num-of-errors"].sum())
    last_depart = int(max(d for _, d in finished.values())) if finished else 0
    treatment = table[table["queue"].isin(["q2", "q3", "q4"])]
    summary = {
        "scenario": sc.name,
        "title": sc.title,
        "study": sc.study,
        "level": sc.level if sc.level is not None else "",
        "total_servers": ed.total_servers(stations),
        "patients": patients,
        "completed": completed,
        "dropped": total_drops,
        "drop_pct": round(100 * total_drops / patients, 2) if patients else 0.0,
        "horizon_steps": horizon,
        "drain_steps": last_depart - horizon,
        "throughput_per_step": round(completed / max(1, last_depart), 3),
        "los_mean": float(o["Avg-response-time"]) if o is not None else float("nan"),
        "los_median": float(o["median-response-time"]) if o is not None else float("nan"),
        "los_p10": float(o["10-response-time"]) if o is not None else float("nan"),
        "los_p90": float(o["90-response-time"]) if o is not None else float("nan"),
        "los_mean_min": round(float(o["Avg-response-time"]) * ed.STEP_MINUTES, 1) if o is not None else float("nan"),
        "los_p90_min": round(float(o["90-response-time"]) * ed.STEP_MINUTES, 1) if o is not None else float("nan"),
        "treatment_wait_mean": round(float(treatment["mean wait"].mean()), 2) if len(treatment) else float("nan"),
        "max_util_station": table.loc[table["utilization"].idxmax(), "station"],
        "max_util": float(table["utilization"].max()),
        "lab_util": float(table.loc[table["queue"] == "q5", "utilization"].iloc[0]) if "q5" in servers else float("nan"),
    }
    at.write_csv_rows(res_dir / "summary.csv", [summary])
    log(f"{sc.name}: patients={patients} completed={completed} dropped={total_drops} "
        f"LOS mean={summary['los_mean']:.1f} p90={summary['los_p90']:.1f} steps; "
        f"hottest={summary['max_util_station']} ({summary['max_util']:.2f})")
    return summary


# --------------------------------------------------------------------------- #
# Cross-scenario comparisons
# --------------------------------------------------------------------------- #
def plot_comparison(rows: list[dict], x_key: str, x_label: str, out: Path, title: str,
                    x_fmt=None, log_x: bool = False) -> None:
    rows = sorted(rows, key=lambda r: r[x_key])
    x = [r[x_key] for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    ax = axes[0]
    ax.plot(x, [r["los_mean"] for r in rows], color=at.PALETTE["blue"], linewidth=2, marker="o", label="mean")
    ax.plot(x, [r["los_p90"] for r in rows], color=at.PALETTE["orange"], linewidth=2, marker="o", label="P90")
    ax.set_ylabel("length of stay (10-min steps)")
    ax.set_title("End-to-end length of stay", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    ax.set_ylim(bottom=0)
    ax = axes[1]
    ax.plot(x, [r["drop_pct"] for r in rows], color=at.PALETTE["red"], linewidth=2, marker="o")
    ax.set_ylabel("% of patients turned away")
    ax.set_title("Errors (QUEUE-FULL)", loc="left", fontsize=10)
    ax.set_ylim(bottom=0)
    ax = axes[2]
    ax.plot(x, [r["throughput_per_step"] for r in rows], color=at.PALETTE["green"], linewidth=2, marker="o")
    ax.set_ylabel("patients leaving per step")
    ax.set_title("Throughput", loc="left", fontsize=10)
    ax.set_ylim(bottom=0)
    for ax in axes:
        at.style_axis(ax)
        ax.set_xlabel(x_label)
        if log_x:
            ax.set_xscale("log")
        if x_fmt:
            ax.set_xticks(x)
            ax.set_xticklabels([x_fmt(v) for v in x])
    fig.suptitle(title, x=0.01, ha="left", color=at.PALETTE["ink"])
    fig.tight_layout()
    fig.savefig(out, dpi=at.DPI)
    plt.close(fig)


def plot_targeted(rows: list[dict], out: Path) -> None:
    labels = [r["scenario"] for r in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, key, ylabel, color in (
        (axes[0], "los_mean", "mean length of stay (steps)", at.PALETTE["blue"]),
        (axes[1], "los_p90", "P90 length of stay (steps)", at.PALETTE["orange"]),
        (axes[2], "drop_pct", "% patients turned away", at.PALETTE["red"]),
    ):
        vals = [r[key] for r in rows]
        bars = ax.bar(x, vals, color=color, width=0.55)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.1f}", ha="center", va="bottom",
                    fontsize=8, color=at.PALETTE["ink"])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel(ylabel)
        at.style_axis(ax)
        ax.grid(axis="x", visible=False)
    axes[0].set_title("Baseline vs +25% everywhere vs targeted changes", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=at.DPI)
    plt.close(fig)


def write_summary(all_rows: list[dict]) -> None:
    res = HERE / "results"
    at.write_csv_rows(res / "summary.csv", all_rows)
    cols = ["scenario", "study", "total_servers", "patients", "completed", "dropped", "drop_pct",
            "throughput_per_step", "los_mean", "los_median", "los_p90", "treatment_wait_mean",
            "max_util_station", "max_util", "lab_util"]
    df = pd.DataFrame(all_rows)[cols]
    (res / "summary.md").write_text(at.df_to_markdown(df) + "\n", encoding="utf-8")

    by = {r["scenario"]: r for r in all_rows}
    base = by.get("base-3k")
    servers = [r for r in all_rows if r["study"] == "servers"]
    if base and servers:
        plot_comparison(servers + [dict(base, level=0.0)], "level", "server change vs baseline",
                        res / "sensitivity-servers.png", "Sensitivity: uniform -30% ... +100% servers (3k patients)",
                        x_fmt=lambda v: f"{v:+.0%}")
    load = [r for r in all_rows if r["study"] == "load"]
    if base and load:
        plot_comparison(load + [dict(base, level=1.0)], "level", "arrival-rate multiplier",
                        res / "load-comparison.png", "Load: same 3k patients at 0.5x / 1x / 1.5x arrival rate",
                        x_fmt=lambda v: f"x{v:g}")
    scale = [r for r in all_rows if r["study"] == "scale"]
    if len(scale) > 1:
        plot_comparison(scale, "level", "patients in the run", res / "scale-comparison.png",
                        "Scale: 1k / 3k / 10k patients at the baseline arrival rate", x_fmt=lambda v: f"{int(v):,}",
                        log_x=True)
    targeted = [by[n] for n in ("base-3k", "srv+25", "lab+1", "pods+1", "pooled-pods", "depth-50") if n in by]
    if len(targeted) > 1:
        plot_targeted(targeted, res / "targeted-comparison.png")


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Obj F (SMALL) ED queueing-network analysis.")
    parser.add_argument("--scenarios", default="all", help="comma list of scenario names (default: all)")
    parser.add_argument("--sim", default=None, help="path to simple-queue-sim / multi-queue-sim binary")
    parser.add_argument("--skip-sim", action="store_true", help="reuse existing runs/<name>/events.log")
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = parser.parse_args(argv)

    scenarios = ed.build_scenarios()
    if args.list:
        for sc in scenarios.values():
            print(f"{sc.name:<12} {sc.study:<9} servers={ed.total_servers(sc.stations):<3} {sc.title}")
        return 0
    wanted = list(scenarios) if args.scenarios == "all" else [s.strip() for s in args.scenarios.split(",")]
    unknown = [w for w in wanted if w not in scenarios]
    if unknown:
        raise SystemExit(f"unknown scenario(s): {unknown}; use --list")

    sim = find_sim(args.sim)
    log(f"simulator: {sim}")
    rows: list[dict] = []
    for name in wanted:
        rows.append(analyze_scenario(scenarios[name], sim, args.skip_sim))

    # Merge with summaries of scenarios not run this time so comparisons stay complete.
    have = {r["scenario"] for r in rows}
    for name in scenarios:
        prev = HERE / "results" / name / "summary.csv"
        if name not in have and prev.exists():
            rows.append(pd.read_csv(prev).iloc[0].to_dict())
    order = {n: i for i, n in enumerate(scenarios)}
    rows.sort(key=lambda r: order.get(r["scenario"], 99))
    write_summary(rows)
    log("done -> results/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

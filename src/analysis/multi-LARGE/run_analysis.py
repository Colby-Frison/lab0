#!/usr/bin/env python3
"""Objective F (LARGE) driver: Internet AS-level packet forwarding.

Reproduces every artifact under this directory:

    workloads/   Obj A generator output, one packet stream per source stub (git-ignored)
    configs/     one qconf.csv per scenario (git-ignored) + base.md summary
    runs/        simulator output per scenario (qmet.csv, events.log, sinks/) -- git-ignored
    results/     plots and tables per scenario + cross-scenario comparisons

Pipeline per scenario:
    as_model (Obj E config + Obj A workloads)  ->  simple-queue-sim
        ->  derive-sys-metrics / plot-sys-metrics  (end-to-end latency, throughput)
        ->  derive-event-metrics                   (per-AS-visit latency)
        ->  filter-by-queue (busiest ASes), filter-by-job (trace packets)
        ->  large_tools.py (all-AS utilization, drops, tables)

Usage:
    python run_analysis.py                  # all scenarios
    python run_analysis.py --scenarios base-100k,srv+50
    python run_analysis.py --skip-sim       # re-run analysis on existing runs/
    python run_analysis.py --list
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

import as_model as am
import large_tools as lt
from large_tools import at, plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OBJC = REPO / "src/implementation/obj-c"
DERIVE_SYS = OBJC / "derive-sys-metrics/derive_sys_metrics.py"
PLOT_SYS = OBJC / "plot-sys-metrics/plot_sys_metrics.py"
DERIVE_EVT = OBJC / "derive-event-metrics/derive_event_metrics.py"
FILTER_Q = OBJC / "filter-by-queue/filter_by_queue.py"
FILTER_J = OBJC / "filter-by-job/filter_by_job.py"
SIM_CANDIDATES = [
    REPO / "src/implementation/obj-b/simple-queue-sim/build/simple-queue-sim.exe",
    REPO / "src/implementation/obj-b/simple-queue-sim/build/simple-queue-sim",
    REPO / "src/implementation/obj-e/multi-queue-sim/build/multi-queue-sim.exe",
    REPO / "src/implementation/obj-e/multi-queue-sim/build/multi-queue-sim",
]
PY = sys.executable
HUB = "1"  # AS number of the largest hub (1,458 links)


def log(msg: str) -> None:
    print(f"[obj-f-large] {msg}", flush=True)


def run(cmd: list, cwd: Path, capture_to: Path | None = None) -> str:
    """Run a CLI; return its stderr (the Obj C tools report counts there)."""
    proc = subprocess.run([str(c) for c in cmd], cwd=str(cwd), text=True, capture_output=True)
    if capture_to is not None:
        with open(capture_to, "a", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(str(c) for c in cmd) + "\n")
            fh.write(proc.stdout[-4000:])
            fh.write(proc.stderr[-4000:])
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
# Model (built once; every scenario shares graph, sources and base servers)
# --------------------------------------------------------------------------- #
class Model:
    def __init__(self) -> None:
        self.net = am.load_graph()
        self.degree = am.degrees(self.net)
        self.stubs = am.stubs(self.net)
        self.sources = am.pick_sources(self.stubs)
        self.qids = am.queue_ids(self.net)
        self.asn = {q: node for node, q in self.qids.items()}
        self.base_servers = am.servers_from_degree(self.degree)

    def by_qid(self, per_node: dict[str, int]) -> dict[str, int]:
        return {self.qids[node]: v for node, v in per_node.items()}


def ensure_workloads(m: Model, sc: am.Scenario) -> dict[str, Path]:
    """Relative workload path per source AS; generated once per packet count."""
    out_dir = Path("workloads") / sc.workload_tag
    paths = {node: out_dir / f"in-{m.qids[node]}.wl" for node in m.sources}
    if not all((HERE / p).exists() for p in paths.values()):
        log(f"generate workloads {out_dir} ({sc.jobs:,} packets over steps 0..{sc.end})")
        am.write_workloads(m.sources, m.qids, sc.jobs, sc.end, HERE / out_dir)
    return paths


def write_base_summary(m: Model, path: Path) -> None:
    srv = list(m.base_servers.values())
    lines = [
        "# Base configuration (`base-100k`)",
        "",
        "| item | value |",
        "|---|---|",
        f"| ASes (queues) | {len(m.net.nodes):,} |",
        f"| links (both directions) | {len(m.net.edges):,} |",
        f"| stub ASes (degree 1) | {len(m.stubs):,} |",
        f"| source stubs | {len(m.sources)} |",
        f"| sinks | every AS ({len(m.net.nodes):,}) |",
        f"| servers | `max(1, ceil(degree / {am.DEGREE_PER_SERVER}))`: total {sum(srv):,}, "
        f"{sum(s > 1 for s in srv)} ASes with more than 1, max {max(srv)} |",
        f"| queue size | `max({am.MIN_QUEUE}, 4 x servers)` |",
        f"| server function | `Sub-1`, rate 1 |",
        f"| packet | one task `W {am.HOPS}` = {am.HOPS} AS visits |",
        f"| edge weight | `{am.EDGE_WEIGHT}` (one round-robin slot per link) |",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Per-scenario pipeline
# --------------------------------------------------------------------------- #
def analyze_scenario(m: Model, sc: am.Scenario, sim: Path, skip_sim: bool) -> dict:
    run_dir = Path("runs") / sc.name
    res_dir = HERE / "results" / sc.name
    cfg_dir = HERE / "configs"
    (HERE / run_dir / "sinks").mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.mkdir(exist_ok=True)
    tool_log = HERE / run_dir / "tool-log.txt"
    if tool_log.exists():
        tool_log.unlink()

    workloads = ensure_workloads(m, sc)
    servers_node = am.scale_servers_total(m.base_servers, sc.server_factor)
    servers = m.by_qid(servers_node)
    degree = m.by_qid(m.degree)
    config = Path("configs") / f"{sc.name}.csv"
    sinks = {node: str(run_dir / "sinks" / f"out-{m.qids[node]}.wl") for node in m.net.nodes}
    am.write_config(m.net, servers_node, {n: str(p) for n, p in workloads.items()}, sinks, HERE / config)
    if sc.name == "base-100k":
        write_base_summary(m, cfg_dir / "base.md")

    qmet, events = run_dir / "qmet.csv", run_dir / "events.log"
    horizon = sc.end + 1
    if not skip_sim or not (HERE / events).exists():
        t0 = time.time()
        run([sim, "--config", config, "--limit", str(horizon * 6), "--qmet", qmet, "--events", events],
            cwd=HERE, capture_to=tool_log)
        log(f"{sc.name}: simulated in {time.time() - t0:.1f}s")

    # --- Obj C tools (CLI) ------------------------------------------------- #
    t0 = time.time()
    sys_csv, sys_all, emet_csv = run_dir / "sysmetrics.csv", run_dir / "sysmetrics-overall.csv", run_dir / "emetrics.csv"
    run([PY, DERIVE_SYS, "--events", events, "--out", sys_csv, "--window", "10", "--dense", "-v"],
        cwd=HERE, capture_to=tool_log)
    run([PY, DERIVE_SYS, "--events", events, "--out", sys_all, "--window", "100000000"],
        cwd=HERE, capture_to=tool_log)
    run([PY, PLOT_SYS, "--sysmetrics", sys_csv, "--out", res_dir / "resplot.png",
         "--title", f"{sc.title}: end-to-end packet latency (10-step windows)"], cwd=HERE, capture_to=tool_log)
    run([PY, DERIVE_EVT, "--events", events, "--out", emet_csv, "-v"], cwd=HERE, capture_to=tool_log)
    log(f"{sc.name}: Obj C metrics in {time.time() - t0:.1f}s")

    # --- all-AS aggregates -------------------------------------------------- #
    steady = (int(horizon * 0.1), int(horizon * 0.9))
    df = lt.with_servers(lt.aggregate_qmet(HERE / qmet, steady), servers, degree)
    emetrics = pd.read_csv(HERE / emet_csv)
    lt.plot_util_vs_degree(df, res_dir / "util-vs-degree.png", f"{sc.title}: utilization of every AS vs its degree")
    lt.plot_util_cdf(df, res_dir / "util-cdf.png", f"{sc.title}: utilization across all ASes")
    lt.plot_drops_by_degree(df, res_dir / "drops-by-degree.png", f"{sc.title}: dropped packets per AS degree class")
    table = lt.per_queue_table(df, emetrics, m.asn)
    table.to_csv(res_dir / "per-queue.csv", index=False)
    (res_dir / "per-queue.md").write_text(at.df_to_markdown(table) + "\n", encoding="utf-8")

    # --- busiest ASes over time (filter-by-queue) --------------------------- #
    top = lt.top_queues(df, 5)
    top_csv = run_dir / "top5-qmet.csv"
    run([PY, FILTER_Q, "--qmet", qmet, "--qid", ",".join(top), "--out", top_csv], cwd=HERE, capture_to=tool_log)
    use = at.compute_use(at.load_qmet(HERE / top_csv), servers)
    labels = {q: f"{q} (AS {m.asn[q]}, {degree[q]} links, {servers[q]} srv)" for q in top}
    lt.plot_top_use({q: use[q] for q in top}, labels, res_dir / "top5-use.png",
                    f"{sc.title}: the 5 busiest ASes")

    # --- trace packets (filter-by-job) -------------------------------------- #
    trace = lt.pick_trace_jobs(emetrics)
    trace_log = res_dir / "trace-jobs.log"
    if trace:
        run([PY, FILTER_J, "--events", events, "--jobs", ",".join(trace), "--out", trace_log],
            cwd=HERE, capture_to=tool_log)

    # --- summary ------------------------------------------------------------ #
    packets = lt.packets_in([HERE / p for p in workloads.values()])
    overall = pd.read_csv(HERE / sys_all)
    o = overall.iloc[0] if len(overall) else None
    delivered = int(overall["throughput"].sum()) if len(overall) else 0
    dropped = int(df["errors"].sum())
    windows = pd.read_csv(HERE / sys_csv)
    active = windows[windows["throughput"] > 0]
    last_depart = int(active["time-step"].max()) + 10 if len(active) else horizon
    busiest = df["utilization"].idxmax()

    def latency(col: str) -> float:
        return round(float(o[col]), 2) if o is not None else float("nan")

    summary = {
        "scenario": sc.name,
        "title": sc.title,
        "study": sc.study,
        "level": sc.level if sc.level is not None else "",
        "total_servers": sum(servers.values()),
        "packets": packets,
        "delivered": delivered,
        "dropped": dropped,
        "drop_pct": round(100 * dropped / packets, 2) if packets else 0.0,
        "horizon_steps": horizon,
        "drain_steps": max(0, last_depart - horizon),
        "throughput_per_step": round(delivered / max(1, last_depart), 3),
        "latency_mean": latency("Avg-response-time"),
        "latency_median": latency("median-response-time"),
        "latency_p10": latency("10-response-time"),
        "latency_p90": latency("90-response-time"),
        "busiest_as": f"{busiest} (AS {m.asn[busiest]})",
        "max_util": round(float(df["utilization"].max()), 3),
        "hub_util": round(float(df.loc[m.qids[HUB], "utilization"]), 3),
        "mean_util": round(float(df["utilization"].mean()), 3),
    }
    at.write_csv_rows(res_dir / "summary.csv", [summary])
    log(f"{sc.name}: packets={packets} delivered={delivered} dropped={dropped} "
        f"latency mean={summary['latency_mean']} p90={summary['latency_p90']}; "
        f"busiest={summary['busiest_as']} ({summary['max_util']:.2f}), hub={summary['hub_util']:.2f}")
    return summary


# --------------------------------------------------------------------------- #
# Cross-scenario comparisons
# --------------------------------------------------------------------------- #
def plot_comparison(rows: list[dict], x_label: str, out: Path, title: str, x_fmt) -> None:
    rows = sorted(rows, key=lambda r: float(r["level"]))
    x = list(range(len(rows)))  # evenly spaced, ordered by level
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    ax = axes[0]
    ax.plot(x, [r["latency_mean"] for r in rows], color=at.PALETTE["blue"], linewidth=2, marker="o", label="mean")
    ax.plot(x, [r["latency_p90"] for r in rows], color=at.PALETTE["orange"], linewidth=2, marker="o", label="P90")
    ax.set_ylabel("end-to-end latency (steps)")
    ax.set_title("Latency", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    axes[1].plot(x, [r["drop_pct"] for r in rows], color=at.PALETTE["red"], linewidth=2, marker="o")
    axes[1].set_ylabel("% of packets dropped")
    axes[1].set_title("Errors (QUEUE-FULL)", loc="left", fontsize=10)
    axes[2].plot(x, [r["throughput_per_step"] for r in rows], color=at.PALETTE["green"], linewidth=2, marker="o")
    axes[2].set_ylabel("packets delivered per step")
    axes[2].set_title("Throughput", loc="left", fontsize=10)
    for ax in axes:
        ax.set_ylim(bottom=0)
        at.style_axis(ax)
        ax.set_xlabel(x_label)
        ax.set_xticks(x)
        ax.set_xticklabels([x_fmt(r) for r in rows], fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", color=at.PALETTE["ink"])
    fig.tight_layout()
    fig.savefig(out, dpi=at.DPI)
    plt.close(fig)


def write_summary(rows: list[dict]) -> None:
    res = HERE / "results"
    at.write_csv_rows(res / "summary.csv", rows)
    cols = ["scenario", "study", "total_servers", "packets", "delivered", "dropped", "drop_pct",
            "throughput_per_step", "latency_mean", "latency_median", "latency_p90", "busiest_as", "max_util",
            "hub_util", "mean_util"]
    (res / "summary.md").write_text(at.df_to_markdown(pd.DataFrame(rows)[cols]) + "\n", encoding="utf-8")

    by = {r["scenario"]: r for r in rows}
    base = by.get("base-100k")
    servers = [r for r in rows if r["study"] == "servers"]
    if base and servers:
        base_total = int(base["total_servers"])

        def server_label(r: dict) -> str:
            # Cuts are pinned by the 1-server minimum, so show the real change in the total too.
            total = int(r["total_servers"]) / base_total - 1
            return f"{float(r['level']):+.0%}\n({total:+.1%})"

        plot_comparison(servers + [dict(base, level=0.0)], "server change per AS (in brackets: change in total servers)",
                        res / "sensitivity-servers.png",
                        "Sensitivity: servers per AS -30% ... +100% (100k packets)", x_fmt=server_label)
    scale = [r for r in rows if r["study"] == "scale"]
    if base and scale:
        plot_comparison(scale + [dict(base, level=float(base["packets"]))], "packets in the run",
                        res / "scale-comparison.png", "Scale: 100k / 300k / 1M packets at 20 packets per step",
                        x_fmt=lambda r: f"{int(float(r['level'])):,}")


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Obj F (LARGE) AS queueing-network analysis.")
    parser.add_argument("--scenarios", default="all", help="comma list of scenario names (default: all)")
    parser.add_argument("--sim", default=None, help="path to simple-queue-sim / multi-queue-sim binary")
    parser.add_argument("--skip-sim", action="store_true", help="reuse existing runs/<name>/events.log")
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = parser.parse_args(argv)

    scenarios = am.build_scenarios()
    if args.list:
        for sc in scenarios.values():
            print(f"{sc.name:<11} {sc.study:<8} packets={sc.jobs:<9,} servers x{sc.server_factor:<5g} {sc.title}")
        return 0
    wanted = list(scenarios) if args.scenarios == "all" else [s.strip() for s in args.scenarios.split(",")]
    unknown = [w for w in wanted if w not in scenarios]
    if unknown:
        raise SystemExit(f"unknown scenario(s): {unknown}; use --list")

    sim = find_sim(args.sim)
    log(f"simulator: {sim}")
    model = Model()
    rows = [analyze_scenario(model, scenarios[name], sim, args.skip_sim) for name in wanted]

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

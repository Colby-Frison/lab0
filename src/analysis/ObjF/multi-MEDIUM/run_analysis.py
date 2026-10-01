#!/usr/bin/env python3
"""MEDIUM study, patterned after ObjF_multi_SMALL. Run --list for scenarios."""

import argparse
import gzip
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "objf-matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import networkx as nx
import email_model as model
import analysis_tools as at

HERE = model.HERE


def build():
    """Compile the existing C++ simulator and allow enough open workload files."""
    try:
        import resource

        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(max(soft, 4096), hard), hard))
    except ImportError:
        pass
    source = HERE.parents[3] / "src/implementation/obj-b/simple-queue-sim/src"
    binary = Path(tempfile.gettempdir()) / "objf-medium-study-sim"
    command = [
        "c++",
        "-std=c++17",
        "-O2",
        *[str(path) for path in sorted(source.glob("*.cpp"))],
        "-o",
        str(binary),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return binary


def simulate(binary, config_path, run_dir, jobs, root=HERE):
    """Run one scenario, reporting simulator diagnostics if it fails."""
    limit = max(20000, int(jobs.arrival.max()) + 100000)
    command = [
        str(binary),
        "--config",
        str(config_path),
        "--limit",
        str(limit),
        "--qmet",
        str(run_dir / "qmet.csv"),
        "--events",
        str(run_dir / "events.log"),
    ]
    process = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(f"Simulator failed:\n{process.stdout}{process.stderr}")


def archive(run_dir):
    """Compress large run outputs and bundle the per-node completion files."""
    for name in ["qmet.csv", "events.log"]:
        path = run_dir / name
        if path.exists():
            with path.open("rb") as source, gzip.open(
                str(path) + ".gz", "wb", compresslevel=6
            ) as destination:
                shutil.copyfileobj(source, destination)
            path.unlink()
    sinks = list(run_dir.glob("out*.wl"))
    if sinks:
        with tarfile.open(run_dir / "sinks.tar.gz", "w:gz") as tar:
            for path in sinks:
                tar.add(path, arcname=path.name)
        for path in sinks:
            path.unlink()


def restore_sinks(run_dir):
    """Restore archived completion files so validation can inspect them."""
    if (run_dir / "sinks.tar.gz").exists():
        with tarfile.open(run_dir / "sinks.tar.gz") as tar:
            tar.extractall(run_dir, filter="data")


def comparisons():
    """Combine saved summaries and plot the four experiment comparisons."""
    rows = []
    for path in sorted((HERE / "results").glob("*/summary.csv")):
        rows.append(pd.read_csv(path))
    if not rows:
        return
    all_summaries = pd.concat(rows, ignore_index=True)
    all_summaries.to_csv(HERE / "results/summary.csv", index=False)
    families = {
        "scale-comparison": ["scale-10k", "base-30k", "scale-100k"],
        "load-comparison": ["load-quiet", "base-30k", "load-surge"],
        "sensitivity-servers": [
            "srv-30",
            "srv-20",
            "srv-10",
            "base-30k",
            "srv+25",
            "srv+50",
            "srv+100",
        ],
        "targeted-comparison": [
            "base-30k",
            "hot+20",
            "cold+20",
            "depth-50",
            "routing-sorted",
        ],
    }
    for name, order in families.items():
        lookup = all_summaries.set_index("scenario")
        available = [s for s in order if s in lookup.index]
        if not available:
            continue
        comparison = lookup.loc[available]
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
        x = np.arange(len(comparison))
        axes[0].bar(x - 0.18, comparison.latency_mean, 0.36, label="Mean")
        axes[0].bar(x + 0.18, comparison.latency_p90, 0.36, label="P90")
        axes[0].legend()
        axes[0].set_ylabel("Completed-job latency (ticks)")
        axes[1].bar(x, comparison.drop_pct, color=at.PALETTE["orange"])
        axes[1].set_ylabel("Dropped requests (%)")
        axes[2].bar(x, comparison.throughput, color=at.PALETTE["aqua"])
        axes[2].set_ylabel("Completed requests/tick")
        for ax in axes:
            ax.set_xticks(x, available, rotation=40, ha="right")
            at.style_axis(ax)
        fig.suptitle(
            name.replace("-", " ").capitalize() + " — fixed workload seed 5113"
        )
        fig.tight_layout()
        fig.savefig(HERE / "results" / f"{name}.png", dpi=130)
        plt.close(fig)


def smoke(binary, root):
    """Check a known route and a deliberately overflowing queue."""
    network = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    scenario = model.Scenario("study-smoke", "validation", jobs=1)
    jobs = pd.DataFrame([dict(job="j0", arrival=0, source=0)])
    counts = {n: 1 for n in network}
    routes = {n: list(network.successors(n)) for n in network}
    config_path, run_dir = model.write_inputs(
        network, scenario, counts, routes, jobs, root=root
    )
    simulate(binary, config_path, run_dir, jobs, root=root)
    visits, job_metrics = at.derive_and_validate(
        run_dir / "events.log",
        jobs,
        network,
        routes,
        counts,
        32,
        pd.read_csv(run_dir / "qmet.csv"),
    )
    assert visits.queue.tolist() == [0, 1, 2, 0] and job_metrics.iloc[0].latency == 11

    # Deliberately overflow a source queue: 1 in service + 32 waiting, 67 rejected.
    drop_sc = model.Scenario("study-drop-check", "validation", jobs=100)
    drop_jobs = pd.DataFrame(
        [dict(job=f"j{i}", arrival=0, source=0) for i in range(100)]
    )
    config_path, run_dir = model.write_inputs(
        network, drop_sc, counts, routes, drop_jobs, root=root
    )
    simulate(binary, config_path, run_dir, drop_jobs, root=root)
    _, drop_metrics = at.derive_and_validate(
        run_dir / "events.log",
        drop_jobs,
        network,
        routes,
        counts,
        32,
        pd.read_csv(run_dir / "qmet.csv"),
    )
    assert (drop_metrics.status == "completed").sum() == 33
    assert (drop_metrics.status == "dropped").sum() == 67


def plot_network(network):
    """Show the selected real network using its adjacency pattern."""
    ranks = {node: rank for rank, node in enumerate(sorted(network))}
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(
        [ranks[v] for u, v in network.edges],
        [ranks[u] for u, v in network.edges],
        s=0.3,
    )
    ax.invert_yaxis()
    ax.set(
        xlabel="Recipient node rank (sorted original IDs)",
        ylabel="Sender node rank (sorted original IDs)",
        title="Network adjacency: 803 queues, 24,138 directed edges",
    )
    fig.tight_layout()
    fig.savefig(HERE / "results/network.png", dpi=150)
    plt.close(fig)


def main():
    """Select scenarios, run or reload each simulation, and update the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--scenarios", help="Comma-separated scenario names")
    parser.add_argument(
        "--skip-sim",
        action="store_true",
        help="Revalidate/replot saved runs without changing their inputs",
    )
    args = parser.parse_args()
    scenario_definitions = model.scenarios()
    if args.list:
        for s in scenario_definitions.values():
            print(
                f"{s.name:18} {s.study:10} jobs={s.jobs:6} load={s.load:g} servers x{s.resource:g} policy={s.policy}"
            )
        return
    selected_scenarios = (
        args.scenarios.split(",") if args.scenarios else list(scenario_definitions)
    )
    if any(s not in scenario_definitions for s in selected_scenarios):
        parser.error("Unknown scenario; use --list")
    for folder in ["results", "configs"]:
        (HERE / folder).mkdir(exist_ok=True)
    network = model.graph()
    binary = None if args.skip_sim else build()
    plot_network(network)
    if binary:
        with tempfile.TemporaryDirectory(prefix="objf-smoke-") as temporary:
            smoke(binary, Path(temporary))
    for name in selected_scenarios:
        started = time.monotonic()
        scenario = scenario_definitions[name]
        counts = model.allocation(network, scenario)
        routes = model.routing(network, scenario.policy == "sorted")
        jobs = model.workload(network, scenario)
        run_dir = HERE / "runs" / name
        result_dir = HERE / "results" / name
        config_path, run_dir = model.write_inputs(
            network, scenario, counts, routes, jobs, check_existing=args.skip_sim
        )
        if args.skip_sim:
            restore_sinks(run_dir)
        else:
            simulate(binary, config_path, run_dir, jobs)
        queue_metrics_path = run_dir / "qmet.csv"
        events_path = run_dir / "events.log"
        if not queue_metrics_path.exists():
            queue_metrics_path = run_dir / "qmet.csv.gz"
        if not events_path.exists():
            events_path = run_dir / "events.log.gz"
        queue_metrics = pd.read_csv(
            queue_metrics_path,
            dtype={
                c: "int32"
                for c in [
                    "time-step",
                    "queue-sys-id",
                    "num-jobs-in-queue",
                    "num-jobs-in-service",
                    "num-of-errors",
                ]
            },
        )
        result = at.dashboard(
            scenario,
            run_dir,
            result_dir,
            jobs,
            network,
            routes,
            counts,
            queue_metrics,
            events_path,
        )
        archive(run_dir)
        print(
            f"{name}: PASS; completed={result['completed']} drops={result['dropped']} mean={result['latency_mean']:.3f} p90={result['latency_p90']:.3f}; {time.monotonic()-started:.1f}s",
            flush=True,
        )
    comparisons()
    from write_report import write_report

    write_report()


if __name__ == "__main__":
    main()

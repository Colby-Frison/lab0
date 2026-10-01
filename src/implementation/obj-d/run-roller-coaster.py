#!/usr/bin/env python3
"""Run the coaster approximation: one tick = one minute; one job = one guest."""
import argparse
import csv
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys


def run(*args, cwd=None):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arrival-period", type=float, default=1 / 0.6,
                        help="Mean minutes between guests (default: 1.6667); arrival rate = 1/period")
    parser.add_argument("--minutes", type=int, default=480, help="Arrival period duration (default: 480)")
    parser.add_argument("--servers", type=int, default=4)
    parser.add_argument("--service-minutes", type=int, default=5)
    parser.add_argument("--queue-capacity", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, help="Output directory (default: obj-d/runs/roller-coaster)")
    parser.add_argument("--simulator", type=Path, help="Path to an already built simulator")
    args = parser.parse_args()
    if not math.isfinite(args.arrival_period) or args.arrival_period <= 0:
        parser.error("--arrival-period must be finite and positive")
    if min(args.minutes, args.servers, args.service_minutes) <= 0 or args.queue_capacity < 0:
        parser.error("duration, servers and service time must be positive; queue capacity must be nonnegative")

    root = Path(__file__).resolve().parent
    # Match the repository's other runners by preferring its Python environment.
    repo = root.parents[2]
    python = next((path for path in (repo / ".venv/Scripts/python.exe",
                                    repo / ".venv/bin/python") if path.is_file()),
                  Path(sys.executable))
    impl = root.parent
    sim_dir = impl / "obj-b/simple-queue-sim"
    out = (args.out or root / "runs/roller-coaster").resolve()
    out.mkdir(parents=True, exist_ok=True)
    candidates = [sim_dir / "build" / name for name in (
        "simple-queue-sim.exe", "simple-queue-sim", "Release/simple-queue-sim.exe",
        "Debug/simple-queue-sim.exe")]
    simulator = args.simulator.resolve() if args.simulator else next(
        (path for path in candidates if path.is_file()), None)
    if simulator is None:
        if not shutil.which("cmake"):
            parser.error("Simulator is not built. Build it first or supply --simulator PATH (automatic build needs CMake).")
        run("cmake", "-S", sim_dir, "-B", sim_dir / "build")
        run("cmake", "--build", sim_dir / "build", "--config", "Release")
        simulator = next((path for path in candidates if path.is_file()), None)
    if simulator is None or not simulator.is_file():
        parser.error("Simulator executable was not found")

    rate = 1 / args.arrival_period
    print(f"Roller coaster: {args.minutes} minutes of Poisson arrivals, seed {args.seed}", flush=True)
    print(f"Mean arrival period: {args.arrival_period:.4f} min ({rate:.3f} guests/min)", flush=True)
    print(f"Servers: {args.servers}; service: {args.service_minutes} min; waiting capacity: {args.queue_capacity}", flush=True)
    print("Individual boarding approximation; trains are not synchronized batches.", flush=True)
    run(python, impl / "obj-a/workload-generator/workload_generator.py",
        "--interval", f"0:{args.minutes - 1}", "--dist", "poisson", "--lam", rate,
        "--task-mode", "fixed", "--fixed-tasks", 1, "--fixed-work", 1,
        "--seed", args.seed, "--out", out / "guests.csv")
    with (out / "coaster-config.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Sys ID", "Queue Max Size", "Num. Servers", "Server Function",
                         "Server Function Rate", "Source", "Sink", "Edges in", "Edges out"])
        writer.writerow(["q0", args.queue_capacity, args.servers, "Sub-1", args.service_minutes,
                         "guests.csv", "boarded.csv", "[]", "[]"])
    run(simulator, "--config", "coaster-config.csv", "--qmet", "qmet.csv",
        "--events", "events.log", cwd=out)
    run(python, impl / "obj-c/derive-event-metrics/derive_event_metrics.py",
        "--events", out / "events.log", "--out", out / "emetrics.csv")

    # Equivalent to: ./compute-use qmet.csv quse.csv. Keep the tool's output intact.
    use_dir = impl / "obj-c/compute-use"
    compute_use = next((use_dir / name for name in ("compute-use", "compute-use.exe")
                        if (use_dir / name).is_file()), None)
    use_status = "Skipped: compute-use executable is not installed."
    if compute_use:
        run(compute_use, "qmet.csv", "quse.csv", cwd=out)
        if not (out / "quse.csv").is_file():
            raise RuntimeError("compute-use completed without creating quse.csv")
        use_status = "Saved compute-use output: quse.csv"
    elif (out / "quse.csv").exists():
        use_status += " Existing quse.csv is from a previous run."

    metrics = rows(out / "qmet.csv")
    active = [row for row in metrics if int(row["time-step"]) < args.minutes]
    jobs = rows(out / "emetrics.csv")
    arrivals = len(rows(out / "guests.csv"))
    print("Generating arrival, waiting-time, and latency/throughput plots...", flush=True)
    plots = []
    if arrivals:
        run(python, impl / "obj-a/workload-visualizer/workload_visualizer.py",
            out / "guests.csv", "--hist", "arrival time", "--bins", 24,
            "--title", "Coaster arrivals (time in minutes)", "--out", out / "arrivals.png")
        plots.append("arrivals.png")
    if jobs:
        run(python, impl / "obj-c/derive-sys-metrics/derive_sys_metrics.py",
            "--events", out / "events.log", "--out", out / "sysmetrics.csv",
            "--window", 1, "--dense")
        run(python, impl / "obj-c/plot-sys-metrics/plot_sys_metrics.py",
            "--sysmetrics", out / "sysmetrics.csv", "--out", out / "latency-throughput.png",
            "--title", "Coaster latency and throughput (one step = one minute)")
        event_plot = impl / "obj-c/plot-derive-event-metrics/plot_derive_event_metrics.py"
        run(python, event_plot, out / "emetrics.csv", out / "waiting-histogram.png",
            "--hist", "time-in-queue", "--bins", 20,
            "--title", "Guest waiting times (minutes)")
        run(python, event_plot, out / "emetrics.csv", out / "waiting-by-arrival.png",
            "--scat", "arrival-time,time-in-queue",
            "--title", "Waiting time by guest arrival (minutes)")
        plots.extend(["latency-throughput.png", "waiting-histogram.png", "waiting-by-arrival.png"])
    completed_active = sum(float(row["arrival-time"]) + float(row["turnaround-time"]) < args.minutes
                           for row in jobs)
    busy = sum(int(row["num-jobs-in-service"]) for row in active)
    waiting = [int(row["num-jobs-in-queue"]) for row in active]
    errors = sum(int(row["num-of-errors"]) for row in metrics)
    capacity = args.servers / args.service_minutes
    report = [
        "ROLLER COASTER RESULTS (one tick = one minute)",
        f"Mean arrival period: {args.arrival_period:.4f} min; seed: {args.seed}",
        f"Nominal capacity: {capacity:.3f} guests/min; offered load: {rate / capacity:.1%}",
        f"Guests generated: {arrivals}; completed after draining: {len(jobs)}",
        f"Utilization during arrival period: {busy / (args.minutes * args.servers):.1%}",
        f"Saturation: average waiting {sum(waiting) / args.minutes:.2f}; peak waiting {max(waiting, default=0)}",
        f"Errors / rejected guests: {errors}",
        f"Throughput during arrival period: {completed_active / args.minutes:.3f} guests/min",
    ]
    for field, label in (("time-in-queue", "Waiting time"), ("turnaround-time", "Total latency")):
        values = sorted(float(row[field]) for row in jobs)
        if values:
            report.append(f"{label}, completed guests: mean {statistics.mean(values):.2f} min; "
                          f"p90 {values[math.ceil(0.9 * len(values)) - 1]:.2f} min (nearest rank)")
        else:
            report.append(f"{label}: no completed guests")
    report.extend([use_status, "Plots: " + (", ".join(plots) or "Skipped: no guests to plot."),
                   f"Files: {out}"])
    summary = "\n".join(report) + "\n"
    (out / "summary.txt").write_text(summary, encoding="utf-8")
    print("\n" + summary)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        sys.exit(f"Run failed: {exc}")

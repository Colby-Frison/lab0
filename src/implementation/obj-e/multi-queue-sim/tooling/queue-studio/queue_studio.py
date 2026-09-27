#!/usr/bin/env python3
"""Interactive multi-queue setup: prompt for parameters, generate, and optionally run.

Metric commands are registered but not implemented. See metrics.py.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "make-queue-inputs"))

import make_queue_inputs as maker  # noqa: E402
import metrics  # noqa: E402

SIM_ROOT = HERE.parent.parent


def ask(label: str, default: str, choices: list[str] | None = None) -> str:
    hint = "/".join(choices) if choices else None
    shown = f"{label} ({hint})" if hint else label
    while True:
        raw = input(f"  {shown} [{default}]: ").strip()
        value = raw or default
        if choices and value not in choices:
            print(f"    choose one of: {', '.join(choices)}")
            continue
        return value


def ask_int(label: str, default: int, minimum: int | None = None) -> int:
    while True:
        raw = ask(label, str(default))
        try:
            value = int(raw)
        except ValueError:
            print("    enter an integer")
            continue
        if minimum is not None and value < minimum:
            print(f"    must be >= {minimum}")
            continue
        return value


def ask_float(label: str, default: float) -> float:
    while True:
        raw = ask(label, str(default))
        try:
            return float(raw)
        except ValueError:
            print("    enter a number")


def collect() -> argparse.Namespace:
    print("Multi-queue studio")
    print("Press Enter to keep the bracketed default.\n")

    dist = ask(
        "Distribution",
        "fixed",
        ["fixed", "uniform", "normal", "geometric", "poisson"],
    )
    ns = argparse.Namespace(
        dist=dist,
        interval=ask("Time interval START:END", "0:9"),
        seed=ask_int("Random seed", 42, 0),
        task_mode=ask("Task mode", "fixed", ["fixed", "dist"]),
        fixed_jobs=1,
        fixed_tasks=1,
        fixed_work=20,
        low=1,
        high=3,
        mu=2.0,
        sigma=1.0,
        p=0.4,
        lam=1.5,
        queues=ask_int("Number of queues", 2, 1),
        max_size=ask_int("Waiting-queue max size", 16, 0),
        servers=ask_int("Servers per queue", 1, 1),
        sub=ask_int("Sub-X amount", 10, 1),
        rate=ask_int("Function rate (ticks between applications)", 10, 1),
        out_dir=ask("Output directory", str(SIM_ROOT / "runs" / "studio")),
    )
    if dist == "fixed":
        ns.fixed_jobs = ask_int("Jobs per time step", 1, 0)
    elif dist == "uniform":
        ns.low = ask_int("Uniform low", 1, 0)
        ns.high = ask_int("Uniform high", 3, 0)
    elif dist == "normal":
        ns.mu = ask_float("Normal mean", 2.0)
        ns.sigma = ask_float("Normal stddev", 1.0)
    elif dist == "geometric":
        ns.p = ask_float("Geometric p (0, 1]", 0.4)
    elif dist == "poisson":
        ns.lam = ask_float("Poisson lambda", 1.5)
    if ns.task_mode == "fixed":
        ns.fixed_tasks = ask_int("Tasks per job", 1, 1)
        ns.fixed_work = ask_int("Work per task", 20, 1)
    return ns


def generate(args: argparse.Namespace) -> dict[str, Path]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    workload = out_dir / "in0.wl"
    subprocess.run(maker.generator_command(args, workload), check=True)
    conf = maker.write_config(args, out_dir, workload)
    print(f"\nworkload: {workload.resolve()}")
    print(f"config:   {conf.resolve()}")
    return {
        "dir": out_dir,
        "workload": workload.resolve(),
        "config": conf.resolve(),
        "sink": (out_dir / "out_final.wl").resolve(),
        "qmet": (out_dir / "qmet.csv").resolve(),
        "events": (out_dir / "events.log").resolve(),
    }


def sim_binary() -> Path:
    exe = SIM_ROOT / "build" / "multi-queue-sim.exe"
    plain = SIM_ROOT / "build" / "multi-queue-sim"
    if exe.is_file():
        return exe
    if plain.is_file():
        return plain
    print("Building multi-queue-sim...")
    subprocess.run(["cmake", "-S", str(SIM_ROOT), "-B", str(SIM_ROOT / "build")], check=True)
    subprocess.run(["cmake", "--build", str(SIM_ROOT / "build")], check=True)
    return exe if exe.is_file() else plain


def run_sim(artifacts: dict[str, Path]) -> None:
    binary = sim_binary()
    subprocess.run(
        [
            str(binary),
            "--config",
            str(artifacts["config"]),
            "--qmet",
            str(artifacts["qmet"]),
            "--events",
            str(artifacts["events"]),
        ],
        check=True,
        cwd=artifacts["dir"],
    )
    print(f"qmet:   {artifacts['qmet']}")
    print(f"events: {artifacts['events']}")
    print(f"sink:   {artifacts['sink']}")


def metrics_menu(artifacts: dict[str, Path] | None) -> None:
    catalog = metrics.CATALOG
    print("\nMetric tools (boilerplate; not implemented yet)")
    for index, tool in enumerate(catalog, start=1):
        print(f"  {index:2d}. [{tool.objective}] {tool.name} - {tool.consumes}")
    print("   Enter to return")
    while True:
        raw = input("  metric #: ").strip()
        if not raw:
            return
        if not raw.isdigit() or not (1 <= int(raw) <= len(catalog)):
            print("    invalid choice")
            continue
        tool = catalog[int(raw) - 1]
        try:
            metrics.run(tool, artifacts)
        except NotImplementedError as exc:
            print(f"    {exc}")


def main() -> int:
    try:
        args = collect()
        if ask("Generate workload and config now?", "y", ["y", "n"]) != "y":
            return 0
        artifacts = generate(args)
        if ask("Run the generated queue now?", "y", ["y", "n"]) == "y":
            run_sim(artifacts)
        if ask("Open the metric menu?", "n", ["y", "n"]) == "y":
            metrics_menu(artifacts)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

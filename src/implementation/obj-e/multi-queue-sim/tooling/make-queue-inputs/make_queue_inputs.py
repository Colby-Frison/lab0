#!/usr/bin/env python3
"""Create an Obj A workload and a multi-queue qconf.csv.

The first queue reads the workload, applies Sub-X once, and forwards along a
chain. The last queue repeats Sub-X until the job is done and writes the sink.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    # .../src/implementation/obj-e/multi-queue-sim/tooling/make-queue-inputs/make_queue_inputs.py
    return Path(__file__).resolve().parents[6]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a workload (.wl) and multi-queue config (qconf.csv)."
    )

    # Queue System Parameters
    parser.add_argument("--out-dir", required=True, help="Directory for in0.wl and qconf.csv")
    parser.add_argument("--queues", type=int, default=2, help="Number of queue systems (>= 1)")

    # Workload Generator Parameters
    parser.add_argument("--interval", default="0:9", help="Inclusive START:END for the generator")
    parser.add_argument(
        "--dist",
        default="fixed",
        choices=["fixed", "uniform", "normal", "geometric", "poisson"],
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--task-mode", choices=["fixed", "dist"], default="fixed")
    parser.add_argument("--fixed-jobs", type=int, default=1)
    parser.add_argument("--fixed-tasks", type=int, default=1)
    parser.add_argument("--fixed-work", type=int, default=20)
    parser.add_argument("--low", type=int, default=1)
    parser.add_argument("--high", type=int, default=3)
    parser.add_argument("--mu", type=float, default=2.0)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--p", type=float, default=0.4)
    parser.add_argument("--lam", type=float, default=1.5)

    # Per-Queue Parameters
    parser.add_argument("--max-size", type=int, default=16)
    parser.add_argument("--servers", type=int, default=1)
    parser.add_argument("--sub", type=int, default=10, help="Sub-X amount")
    parser.add_argument("--rate", type=int, default=10, help="Server function rate")
    return parser


def generator_command(args: argparse.Namespace, workload: Path) -> list[str]:
    gen = repo_root() / "src/implementation/obj-a/workload-generator/workload_generator.py"
    cmd = [
        sys.executable,
        str(gen),
        "--interval",
        args.interval,
        "--dist",
        args.dist,
        "--seed",
        str(args.seed),
        "--task-mode",
        args.task_mode,
        "--fixed-tasks",
        str(args.fixed_tasks),
        "--fixed-work",
        str(args.fixed_work),
        "--out",
        str(workload),
    ]
    extras = {
        "fixed": ["--fixed-jobs", str(args.fixed_jobs)],
        "uniform": ["--low", str(args.low), "--high", str(args.high)],
        "normal": ["--mu", str(args.mu), "--sigma", str(args.sigma)],
        "geometric": ["--p", str(args.p)],
        "poisson": ["--lam", str(args.lam)],
    }
    cmd.extend(extras[args.dist])
    return cmd


def write_config(args: argparse.Namespace, out_dir: Path, workload: Path) -> Path:
    sink = (out_dir / "out_final.wl").resolve()
    workload = workload.resolve()
    header = (
        "Sys ID,Queue Max Size,Num. Servers,Server Function,"
        "Server Function Rate,Source,Sink,Edges in,Edges out\n"
    )
    lines = [header]
    fn = f"Sub-{args.sub}"
    last = args.queues - 1
    for i in range(args.queues):
        qid = f"q{i}"
        source = str(workload) if i == 0 else ""
        if i == last:
            function = f"{fn}*"
            sink_path = str(sink)
            edges_in = "[]" if i == 0 else f"[q{i - 1}]"
            edges_out = "[]"
        else:
            function = fn
            sink_path = ""
            edges_in = "[]" if i == 0 else f"[q{i - 1}]"
            edges_out = f"[q{i + 1}]"
        lines.append(
            f"{qid},{args.max_size},{args.servers},{function},{args.rate},"
            f"{source},{sink_path},{edges_in},{edges_out}\n"
        )
    conf = out_dir / "qconf.csv"
    conf.write_text("".join(lines), encoding="utf-8", newline="\n")
    return conf


def main() -> int:
    args = build_parser().parse_args()
    if args.queues < 1:
        print("--queues must be >= 1", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    workload = out_dir / "in0.wl"
    subprocess.run(generator_command(args, workload), check=True)
    conf = write_config(args, out_dir, workload)
    print(f"workload: {workload.resolve()}")
    print(f"config:   {conf.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

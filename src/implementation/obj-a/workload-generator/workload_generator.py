#!/usr/bin/env python3
"""Synthetic workload generator for Queue Lab Objective A."""

from __future__ import annotations

import argparse
import json
import random
import sys
from typing import Callable


DrawFn = Callable[[], int]


def parse_interval(value: str) -> tuple[int, int]:
    """Parse START:END as an inclusive time-step range."""
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            "interval must be START:END (inclusive), e.g. 0:50"
        )
    try:
        start, end = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("interval bounds must be integers") from exc
    if end < start:
        raise argparse.ArgumentTypeError("interval END must be >= START")
    return start, end


def make_draw(dist: str, args: argparse.Namespace, rng: random.Random) -> DrawFn:
    """Return a sampler that yields non-negative integers (0 allowed)."""
    if dist == "fixed":
        k = args.fixed_jobs
        return lambda: k

    if dist == "uniform":
        low, high = args.low, args.high
        return lambda: rng.randint(low, high)

    if dist == "normal":
        mu, sigma = args.mu, args.sigma

        def draw_normal() -> int:
            return max(0, int(round(rng.gauss(mu, sigma))))

        return draw_normal

    if dist == "geometric":
        p = args.p

        def draw_geometric() -> int:
            # Failures before first success so that 0 is possible.
            return _geometric(rng, p) - 1

        return draw_geometric

    if dist == "poisson":
        lam = args.lam

        def draw_poisson() -> int:
            return _poisson(rng, lam)

        return draw_poisson

    raise ValueError(f"unknown distribution: {dist}")


def _geometric(rng: random.Random, p: float) -> int:
    """Trials until first success (minimum 1), matching numpy.random.geometric."""
    if not 0 < p <= 1:
        raise ValueError("geometric p must be in (0, 1]")
    trials = 1
    while rng.random() > p:
        trials += 1
    return trials


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth Poisson sampler."""
    if lam < 0:
        raise ValueError("poisson lambda must be >= 0")
    L = pow(2.718281828459045, -lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def generate_jobs(
    start: int,
    end: int,
    draw: DrawFn,
    task_mode: str,
    fixed_tasks: int,
    fixed_work: int,
) -> list[dict]:
    jobs: list[dict] = []
    next_id = 0

    for t in range(start, end + 1):
        n_jobs = draw()
        for _ in range(n_jobs):
            if task_mode == "fixed":
                n_tasks = fixed_tasks
                works = [fixed_work] * n_tasks
            else:
                n_tasks = max(1, draw())
                works = [max(1, draw()) for _ in range(n_tasks)]

            tasks = [f"{tid}: W {works[tid]}" for tid in range(n_tasks)]
            jobs.append(
                {
                    "Job Id": f"j{next_id}",
                    "arrival time": t,
                    "Tasks": tasks,
                }
            )
            next_id += 1

    jobs.sort(key=lambda j: (j["arrival time"], int(j["Job Id"][1:])))
    return jobs


def write_workload(jobs: list[dict], out) -> None:
    # Match examples/obj-a/wl-*.csv: always quote Tasks with doubled inner quotes.
    out.write("Job Id,arrival time,Tasks\n")
    for job in jobs:
        tasks_json = json.dumps(job["Tasks"])
        escaped = tasks_json.replace('"', '""')
        out.write(f'{job["Job Id"]},{job["arrival time"]},"{escaped}"\n')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic queueing workload CSV."
    )
    parser.add_argument(
        "--interval",
        type=parse_interval,
        required=True,
        help="Inclusive time-step range START:END",
    )
    parser.add_argument(
        "--dist",
        required=True,
        choices=["fixed", "uniform", "normal", "geometric", "poisson"],
        help="Distribution for jobs/step (and tasks/work when --task-mode=dist)",
    )
    parser.add_argument("--seed", type=int, default=None, help="RNG seed")
    parser.add_argument("--out", default=None, help="Output CSV path (default: stdout)")

    parser.add_argument("--fixed-jobs", type=int, default=None, help="Jobs per step (fixed)")
    parser.add_argument("--low", type=int, default=None, help="Uniform inclusive low")
    parser.add_argument("--high", type=int, default=None, help="Uniform inclusive high")
    parser.add_argument("--mu", type=float, default=None, help="Normal mean")
    parser.add_argument("--sigma", type=float, default=None, help="Normal stddev")
    parser.add_argument("--p", type=float, default=None, help="Geometric success probability")
    parser.add_argument("--lam", type=float, default=None, help="Poisson lambda")

    parser.add_argument(
        "--task-mode",
        choices=["fixed", "dist"],
        default="dist",
        help="fixed: use --fixed-tasks/--fixed-work; dist: sample from --dist (default)",
    )
    parser.add_argument("--fixed-tasks", type=int, default=1, help="Tasks per job if task-mode=fixed")
    parser.add_argument("--fixed-work", type=int, default=1, help="Work N per task if task-mode=fixed")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    dist = args.dist
    if dist == "fixed":
        if args.fixed_jobs is None or args.fixed_jobs < 0:
            raise SystemExit("--dist fixed requires --fixed-jobs >= 0")
    elif dist == "uniform":
        if args.low is None or args.high is None:
            raise SystemExit("--dist uniform requires --low and --high")
        if args.low < 0 or args.high < args.low:
            raise SystemExit("uniform requires 0 <= --low <= --high")
    elif dist == "normal":
        if args.mu is None or args.sigma is None:
            raise SystemExit("--dist normal requires --mu and --sigma")
        if args.sigma < 0:
            raise SystemExit("--sigma must be >= 0")
    elif dist == "geometric":
        if args.p is None or not (0 < args.p <= 1):
            raise SystemExit("--dist geometric requires --p in (0, 1]")
    elif dist == "poisson":
        if args.lam is None or args.lam < 0:
            raise SystemExit("--dist poisson requires --lam >= 0")

    if args.task_mode == "fixed":
        if args.fixed_tasks < 1:
            raise SystemExit("--fixed-tasks must be >= 1")
        if args.fixed_work < 1:
            raise SystemExit("--fixed-work must be >= 1")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args)

    rng = random.Random(args.seed)
    draw = make_draw(args.dist, args, rng)
    start, end = args.interval
    jobs = generate_jobs(
        start,
        end,
        draw,
        args.task_mode,
        args.fixed_tasks,
        args.fixed_work,
    )

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            write_workload(jobs, f)
    else:
        write_workload(jobs, sys.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""filter-by-job — Queue Lab Objective C.

Read the shared event log written by the simulator (Obj B / Obj E) and keep
only the lines of one or more jobs:

    <time> <job-id> IN <qsid> <EVENT> <rest>

The job id is always the second token, and only that token is compared (exact
match), so ``j1`` never matches ``j10`` and a ``j0`` elsewhere on a line is
ignored. Lines are written unchanged, in their original order.

``--jobs`` accepts ``j0`` or a bare ``0`` (the event log uses ``j0``).

Usage:
    python filter_by_job.py --events events.log --jobs 0[,1,...] [--out jobout.log]
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, Iterator, TextIO


# --------------------------------------------------------------------------- #
# Job id arguments
# --------------------------------------------------------------------------- #
def normalize_job_id(token: str) -> str:
    """Map a CLI job id to the form the event log uses: ``0`` / ``007`` -> ``j0`` / ``j7``."""
    token = token.strip()
    if not token:
        raise ValueError("empty job id")
    return f"j{int(token)}" if token.isdigit() else token


def parse_job_ids(spec: str) -> list[str]:
    """Parse ``"0, j1,1"`` -> ``["j0", "j1"]`` (normalized, de-duplicated, order kept)."""
    job_ids: list[str] = []
    for token in spec.split(","):
        job_id = normalize_job_id(token)
        if job_id not in job_ids:
            job_ids.append(job_id)
    return job_ids


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #
def filter_by_job(lines: Iterable[str], job_ids: Iterable[str]) -> Iterator[str]:
    """Yield the lines whose second token is one of ``job_ids`` (unchanged)."""
    wanted = set(job_ids)
    for line in lines:
        parts = line.split(maxsplit=2)
        if len(parts) >= 2 and parts[1] in wanted:
            yield line


def write_lines(lines: Iterable[str], out: TextIO) -> None:
    out.writelines(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Keep only the event-log lines of the given job(s)."
    )
    parser.add_argument("--events", required=True, help="Path to the event log (events.log)")
    parser.add_argument(
        "--jobs",
        required=True,
        help="Job id or comma-separated list, e.g. j0 or 0,1 (0 is accepted as j0)",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="Output log path (default: '-' = stdout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        job_ids = parse_job_ids(args.jobs)
    except ValueError as exc:
        raise SystemExit(f"filter-by-job: --jobs: {exc}") from exc

    try:
        with open(args.events, encoding="utf-8") as fh:
            filtered = filter_by_job(fh, job_ids)
            if args.out == "-":
                write_lines(filtered, sys.stdout)
            else:
                with open(args.out, "w", encoding="utf-8", newline="") as out:
                    write_lines(filtered, out)
    except OSError as exc:
        raise SystemExit(f"filter-by-job: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

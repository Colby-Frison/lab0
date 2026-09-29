#!/usr/bin/env python3
"""filter-by-queue — Queue Lab Objective C.

Read the per-queue metrics file written by the simulator (Obj B / Obj E) and
keep only the rows of one or more queue systems:

    time-step, queue-sys-id, num-jobs-in-queue, num-jobs-in-service, num-of-errors

The simulator writes numeric queue ids (``q0`` in the config becomes ``0`` in
qmet.csv). ``--qid`` accepts either form; the file column is compared exactly.
Rows keep their original order and formatting.

Usage:
    python filter_by_queue.py --qmet qmet.csv --qid 0[,1,...] [--out qmetout.csv]
                              [--verbose]
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Iterable, TextIO

import pandas as pd

QUEUE_COLUMN = "queue-sys-id"

_QID_RE = re.compile(r"(\d+)$")


# --------------------------------------------------------------------------- #
# Queue id arguments
# --------------------------------------------------------------------------- #
def normalize_qid(token: str) -> str:
    """Map a CLI queue id to the numeric form qmet.csv uses: ``q0`` / ``007`` -> ``0``.
    """
    token = token.strip()
    match = _QID_RE.search(token)
    if not match:
        raise ValueError(f"invalid queue id {token!r} (expected e.g. 0 or q0)")
    return str(int(match.group(1)))


def parse_qids(spec: str) -> list[str]:
    """Parse ``"0, q2,2"`` -> ``["0", "2"]`` (normalized, de-duplicated, order kept)."""
    qids: list[str] = []
    for token in spec.split(","):
        qid = normalize_qid(token)
        if qid not in qids:
            qids.append(qid)
    return qids


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #
def read_qmet(source: str | TextIO) -> pd.DataFrame:
    """Read qmet.csv with every cell kept as its exact text."""
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    if QUEUE_COLUMN not in df.columns:
        raise ValueError(f"missing column {QUEUE_COLUMN!r} (got {list(df.columns)})")
    return df


def filter_by_queue(df: pd.DataFrame, qids: Iterable[str]) -> pd.DataFrame:
    """Keep the rows whose queue-sys-id is one of ``qids`` (original order)."""
    return df[df[QUEUE_COLUMN].isin(set(qids))]


def write_qmet(df: pd.DataFrame, out: TextIO) -> None:
    df.to_csv(out, index=False, lineterminator="\n")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Keep only the qmet.csv rows of the given queue system(s)."
    )
    parser.add_argument(
        "--qmet",
        required=True,
        help="Path to qmet.csv written by the simulator ('-' = stdin)",
    )
    parser.add_argument(
        "--qid",
        required=True,
        help="Queue id or comma-separated list, e.g. 0 or 0,2 (q0 is accepted as 0)",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="Output CSV path (default: '-' = stdout)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Print a summary to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def warn(message: str) -> None:
        print(f"filter-by-queue: {message}", file=sys.stderr)

    try:
        qids = parse_qids(args.qid)
    except ValueError as exc:
        raise SystemExit(f"filter-by-queue: --qid: {exc}") from exc

    try:
        df = read_qmet(sys.stdin if args.qmet == "-" else args.qmet)
    except OSError as exc:
        raise SystemExit(f"filter-by-queue: cannot read {args.qmet}: {exc}") from exc
    except pd.errors.EmptyDataError as exc:
        raise SystemExit(f"filter-by-queue: {args.qmet} is empty") from exc
    except ValueError as exc:
        raise SystemExit(f"filter-by-queue: {args.qmet}: {exc}") from exc

    filtered = filter_by_queue(df, qids)
    available = list(dict.fromkeys(df[QUEUE_COLUMN]))
    missing = [qid for qid in qids if qid not in available]

    if args.out == "-":
        write_qmet(filtered, sys.stdout)
    else:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            write_qmet(filtered, fh)

    if missing:
        warn(
            f"queue id(s) {','.join(missing)} not found in {args.qmet}; "
            f"available: {','.join(available) or '(none)'}"
        )
    if args.verbose:
        print(
            "filter-by-queue: "
            f"qids={qids} "
            f"queues_in_file={available} "
            f"rows_in={len(df)} rows_out={len(filtered)}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""compute-use — Queue Lab Objective C.

Read qmet.csv and the queue config, and write one USE row per time step and
queue. Windows of 10, 100, and 1000 steps are computed separately for each
queue, using only the steps that exist so far:

    Utilization = mean(num-jobs-in-service / Num. Servers)
    Saturation  = mean(num-jobs-in-queue)
    Errors      = sum(num-of-errors)

Usage:
    python compute_use.py --qmet qmet.csv --config qconf.csv [--out quse.csv]
                          [--verbose]
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import TextIO

import pandas as pd

WINDOWS = (10, 100, 1000)
QMET_COLUMNS = (
    "time-step",
    "queue-sys-id",
    "num-jobs-in-queue",
    "num-jobs-in-service",
    "num-of-errors",
)
VALUE_COLUMNS = tuple(
    name
    for size in WINDOWS
    for name in (f"Utilization({size})", f"Saturation({size})", f"Errors({size})")
)
OUT_COLUMNS = ("time-step", "queue-sys-id", *VALUE_COLUMNS)

_QID_RE = re.compile(r"(\d+)$")


def normalize_qid(token: str) -> str:
    """Map ``q0`` / ``007`` to the numeric id qmet.csv stores: ``0``."""
    match = _QID_RE.search(token.strip())
    if not match:
        raise ValueError(f"invalid queue id {token!r}")
    return str(int(match.group(1)))


def load_server_counts(path: str) -> dict[str, int]:
    """Map each config queue id to Num. Servers.

    Only the first three fields are read, so commas inside an edge list do
    not shift the server count.
    """
    counts: dict[str, int] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        header = fh.readline()
        if not header:
            raise ValueError("config is empty")
        for line_no, raw in enumerate(fh, start=2):
            line = raw.strip()
            if not line:
                continue
            fields = line.split(",", 3)
            if len(fields) < 3:
                raise ValueError(f"config line {line_no} has no server count")
            qid = normalize_qid(fields[0])
            try:
                servers = int(fields[2])
            except ValueError as exc:
                raise ValueError(f"config line {line_no}: bad server count {fields[2]!r}") from exc
            if servers < 1:
                raise ValueError(f"queue {qid} has no servers")
            counts[qid] = servers
    if not counts:
        raise ValueError("config has no queue rows")
    return counts


def read_qmet(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [name for name in QMET_COLUMNS if name not in df.columns]
    if missing:
        raise ValueError(f"missing columns {missing}")
    return df


def _series(df: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(df[column], errors="coerce")
    if values.isna().any():
        raise ValueError(f"non-numeric {column}")
    return values


def compute_use(qmet: pd.DataFrame, server_counts: dict[str, int]) -> pd.DataFrame:
    """One row per qmet row, windows filled from that queue's own history."""
    rows: list[dict] = []
    grouped = qmet.groupby(qmet["queue-sys-id"].map(normalize_qid), sort=False)
    for qid, frame in grouped:
        if qid not in server_counts:
            raise ValueError(f"queue {qid} is in qmet.csv but not in the config")
        frame = frame.copy()
        frame["_time"] = _series(frame, "time-step")
        frame = frame.sort_values("_time", kind="mergesort")
        busy = _series(frame, "num-jobs-in-service") / server_counts[qid]
        waiting = _series(frame, "num-jobs-in-queue")
        drops = _series(frame, "num-of-errors")
        for index in range(len(frame)):
            row = {
                "time-step": int(frame["_time"].iloc[index]),
                "queue-sys-id": qid,
            }
            for size in WINDOWS:
                start = max(0, index - size + 1)
                row[f"Utilization({size})"] = round(float(busy.iloc[start : index + 1].mean()), 6)
                row[f"Saturation({size})"] = round(float(waiting.iloc[start : index + 1].mean()), 6)
                row[f"Errors({size})"] = int(drops.iloc[start : index + 1].sum())
            rows.append(row)
    out = pd.DataFrame(rows, columns=list(OUT_COLUMNS))
    if out.empty:
        return out
    order = out["queue-sys-id"].astype(int)
    return (
        out.assign(_order=order)
        .sort_values(["time-step", "_order"], kind="mergesort")
        .drop(columns="_order")
        .reset_index(drop=True)
    )


def write_quse(df: pd.DataFrame, out: TextIO) -> None:
    df.to_csv(out, index=False, lineterminator="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute sliding-window USE metrics from qmet.csv.")
    parser.add_argument("--qmet", required=True, help="qmet.csv written by the simulator")
    parser.add_argument("--config", required=True, help="qconf.csv (used for Num. Servers)")
    parser.add_argument("--out", default="-", help="Output CSV path (default: '-' = stdout)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print a summary to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        counts = load_server_counts(args.config)
        qmet = read_qmet(args.qmet)
        result = compute_use(qmet, counts)
    except (OSError, ValueError, pd.errors.EmptyDataError) as exc:
        raise SystemExit(f"compute-use: {exc}") from exc

    if args.out == "-":
        write_quse(result, sys.stdout)
    else:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            write_quse(result, fh)

    if args.verbose:
        queues = list(dict.fromkeys(result["queue-sys-id"])) if not result.empty else []
        print(
            f"compute-use: queues={queues} rows_in={len(qmet)} rows_out={len(result)}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

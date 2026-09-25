#!/usr/bin/env python3
"""derive-sys-metrics — Queue Lab Objective C.

Read the shared event log written by the simulator (Obj B / Obj E) and build a
time series of *system-level* metrics for jobs that enter the simulator through
a source workload and leave through a sink workload:

    time-step, Avg-response-time, median-response-time,
    10-response-time, 90-response-time, throughput

Response time here is end-to-end: the time step a job DEPARTs to a sink minus
the time step it ARRIVEd from a source. Throughput is the number of jobs that
left the simulator at that time step (or within that window of steps).

Internal edges (a DEPART-VIA / ARRIVE-VIA whose edge is another queue system,
e.g. ``DEPART-VIA q1``) are hops inside the network and are ignored here; they
are covered per visit by derive-event-metrics.

Usage:
    python derive_sys_metrics.py --events events.log [--out sysmetrics.csv]
                                 [--window W] [--dense] [--verbose]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, TextIO

import numpy as np

HEADER = [
    "time-step",
    "Avg-response-time",
    "median-response-time",
    "10-response-time",
    "90-response-time",
    "throughput",
]

Warn = Callable[[str], None]


# --------------------------------------------------------------------------- #
# Event log parsing
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Event:
    """One line of the event log: ``<time> <job-id> IN <qsid> <EVENT> <rest>``."""

    time: int
    job: str
    qsid: str
    kind: str
    rest: str = ""


def parse_event(line: str) -> Event | None:
    """Parse one event-log line; return None when the line is not an event."""
    parts = line.split(maxsplit=5)
    if len(parts) < 5 or parts[2] != "IN":
        return None
    try:
        time = int(parts[0])
    except ValueError:
        return None
    rest = parts[5].strip() if len(parts) > 5 else ""
    return Event(time, parts[1], parts[3], parts[4], rest)


def iter_events(lines: Iterable[str], warn: Warn | None = None) -> Iterator[Event]:
    """Yield parsed events, skipping blank lines and warning on malformed ones."""
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        event = parse_event(line)
        if event is None:
            if warn:
                warn(f"line {lineno}: not an event line, skipped: {line.rstrip()}")
            continue
        yield event


def collect_queue_ids(events: Iterable[Event]) -> set[str]:
    """Every queue-system id that appears in the log (the ``IN <qsid>`` token)."""
    return {event.qsid for event in events}


# --------------------------------------------------------------------------- #
# Metric derivation
# --------------------------------------------------------------------------- #
@dataclass
class Summary:
    """Bookkeeping for the run; printed with --verbose."""

    queue_ids: set[str] = field(default_factory=set)
    source_arrivals: int = 0
    sink_departures: int = 0
    unmatched_departures: int = 0  # DEPART to a sink with no open source arrival
    still_in_system: int = 0  # source arrivals that never reached a sink
    max_time: int | None = None


@dataclass(frozen=True)
class SysMetricsRow:
    time_step: int
    avg: float | None
    median: float | None
    p10: float | None
    p90: float | None
    throughput: int

    def as_csv(self) -> list[str]:
        def fmt(value: float | None) -> str:
            return "" if value is None else f"{value:.2f}"

        return [
            str(self.time_step),
            fmt(self.avg),
            fmt(self.median),
            fmt(self.p10),
            fmt(self.p90),
            str(self.throughput),
        ]


def collect_response_times(
    events: Iterable[Event],
    queue_ids: set[str],
    window: int = 1,
    summary: Summary | None = None,
) -> dict[int, list[int]]:
    """Map each departure bucket -> list of end-to-end response times.

    A bucket is ``(departure_time // window) * window``; with ``window == 1`` it
    is simply the departure time step. Arrivals are matched to departures per
    job id in FIFO order, so a job id that re-enters through a source (or
    duplicate ids across several source files) still pairs sensibly.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    summary = summary if summary is not None else Summary()
    summary.queue_ids = set(queue_ids)

    open_arrivals: dict[str, deque[int]] = defaultdict(deque)
    by_bucket: dict[int, list[int]] = defaultdict(list)

    for event in events:
        summary.max_time = (
            event.time if summary.max_time is None else max(summary.max_time, event.time)
        )
        if event.kind == "ARRIVE-VIA":
            if event.rest not in queue_ids:  # from a source, not a peer queue
                open_arrivals[event.job].append(event.time)
                summary.source_arrivals += 1
        elif event.kind == "DEPART-VIA":
            if event.rest not in queue_ids:  # to a sink, not a peer queue
                pending = open_arrivals.get(event.job)
                if pending:
                    arrived = pending.popleft()
                    bucket = (event.time // window) * window
                    by_bucket[bucket].append(event.time - arrived)
                    summary.sink_departures += 1
                else:
                    summary.unmatched_departures += 1

    summary.still_in_system = sum(len(q) for q in open_arrivals.values())
    return dict(by_bucket)


def build_rows(
    by_bucket: dict[int, list[int]],
    window: int = 1,
    dense: bool = False,
    max_time: int | None = None,
) -> list[SysMetricsRow]:
    """Aggregate response times per bucket into output rows (sorted by time)."""
    if dense:
        last = max_time if max_time is not None else (max(by_bucket) if by_bucket else -1)
        if last < 0:
            steps: Iterable[int] = []
        else:
            steps = range(0, (last // window) * window + 1, window)
    else:
        steps = sorted(by_bucket)

    rows: list[SysMetricsRow] = []
    for step in steps:
        latencies = by_bucket.get(step)
        if not latencies:
            rows.append(SysMetricsRow(step, None, None, None, None, 0))
            continue
        arr = np.asarray(latencies, dtype=float)
        rows.append(
            SysMetricsRow(
                time_step=step,
                avg=float(arr.mean()),
                median=float(np.median(arr)),
                p10=float(np.percentile(arr, 10)),
                p90=float(np.percentile(arr, 90)),
                throughput=int(arr.size),
            )
        )
    return rows


def derive_system_metrics(
    lines: Iterable[str],
    window: int = 1,
    dense: bool = False,
    warn: Warn | None = None,
    summary: Summary | None = None,
) -> list[SysMetricsRow]:
    """Convenience wrapper for in-memory logs (tests): lines -> rows."""
    lines = list(lines)
    queue_ids = collect_queue_ids(iter_events(lines))
    summary = summary if summary is not None else Summary()
    by_bucket = collect_response_times(iter_events(lines, warn), queue_ids, window, summary)
    return build_rows(by_bucket, window, dense, summary.max_time)


def write_rows(rows: Iterable[SysMetricsRow], out: TextIO) -> None:
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow(row.as_csv())


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Derive system response-time percentiles and throughput per time step "
            "from a simulator event log."
        )
    )
    parser.add_argument("--events", required=True, help="Path to the event log (job.log / events.log)")
    parser.add_argument(
        "--out",
        default="-",
        help="Output CSV path (default: '-' = stdout)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=1,
        help="Group departures into windows of W time steps (default 1 = per step)",
    )
    parser.add_argument(
        "--dense",
        action="store_true",
        help="Emit a row for every window from 0 to the last event, throughput 0 where no job left",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Print a summary to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.window < 1:
        raise SystemExit("--window must be >= 1")

    def warn(message: str) -> None:
        print(f"derive-sys-metrics: {message}", file=sys.stderr)

    summary = Summary()
    try:
        # Pass 1: learn the queue ids so internal hops can be told from sources/sinks.
        with open(args.events, encoding="utf-8") as fh:
            queue_ids = collect_queue_ids(iter_events(fh))
        # Pass 2: pair source arrivals with sink departures.
        with open(args.events, encoding="utf-8") as fh:
            by_bucket = collect_response_times(
                iter_events(fh, warn), queue_ids, args.window, summary
            )
    except OSError as exc:
        raise SystemExit(f"derive-sys-metrics: cannot read {args.events}: {exc}") from exc

    rows = build_rows(by_bucket, args.window, args.dense, summary.max_time)

    if args.out == "-":
        write_rows(rows, sys.stdout)
    else:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            write_rows(rows, fh)

    if summary.unmatched_departures:
        warn(f"{summary.unmatched_departures} sink departure(s) had no matching source arrival")
    if summary.still_in_system:
        warn(
            f"{summary.still_in_system} source arrival(s) never reached a sink "
            "(dropped, or still in the system when the run ended)"
        )
    if args.verbose:
        print(
            "derive-sys-metrics: "
            f"queues={sorted(summary.queue_ids)} "
            f"source_arrivals={summary.source_arrivals} "
            f"sink_departures={summary.sink_departures} "
            f"rows={len(rows)} window={args.window} dense={args.dense}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

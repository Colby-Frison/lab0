#!/usr/bin/env python3
"""derive-event-metrics — Queue Lab Objective C.

Read the shared event log written by the simulator (Obj B / Obj E) and emit one
row per *visit* of a job to a queue system:

    Job-id, Queue-sys-id, arrival-time, time-in-queue, time-in-service,
    response-time, turnaround-time

A visit starts at ``ARRIVE-VIA`` and ends at ``EXITS-SERVER`` in the same queue.
A job may visit several queues (or the same queue more than once); each visit
is its own row. Visits that were rejected (``ERROR QUEUE-FULL``) never entered
a server, so they have no row; they are counted and reported on stderr.

Definitions (PDF §C, "Derived Job Metrics"):
    arrival-time     time step the job arrived in this queue (ARRIVE-VIA)
    time-in-queue    ENTERS-SERVER - ARRIVE-VIA            (waiting time)
    time-in-service  EXITS-SERVER - ENTERS-SERVER
    response-time    time until the job first enters a server (= time-in-queue)
    turnaround-time  time-in-queue + time-in-service (= EXITS-SERVER - ARRIVE-VIA)

Usage:
    python derive_event_metrics.py --events events.log [--out emetrics.csv] [--verbose]
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, TextIO

HEADER = [
    "Job-id",
    "Queue-sys-id",
    "arrival-time",
    "time-in-queue",
    "time-in-service",
    "response-time",
    "turnaround-time",
]

Warn = Callable[[str], None]


# --------------------------------------------------------------------------- #
# Event log parsing (same line grammar as derive-sys-metrics)
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
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        event = parse_event(line)
        if event is None:
            if warn:
                warn(f"line {lineno}: not an event line, skipped: {line.rstrip()}")
            continue
        yield event


# --------------------------------------------------------------------------- #
# Visit tracking
# --------------------------------------------------------------------------- #
@dataclass
class OpenVisit:
    arrival: int
    entered: int | None = None  # first ENTERS-SERVER (or TASK-START) in this queue


@dataclass(frozen=True)
class VisitRow:
    job: str
    qsid: str
    arrival: int
    entered: int
    exited: int

    @property
    def time_in_queue(self) -> int:
        return self.entered - self.arrival

    @property
    def time_in_service(self) -> int:
        return self.exited - self.entered

    @property
    def response_time(self) -> int:
        return self.time_in_queue

    @property
    def turnaround_time(self) -> int:
        return self.exited - self.arrival

    def as_csv(self) -> list[str]:
        return [
            self.job,
            self.qsid,
            str(self.arrival),
            str(self.time_in_queue),
            str(self.time_in_service),
            str(self.response_time),
            str(self.turnaround_time),
        ]


@dataclass
class Summary:
    visits: int = 0
    dropped: int = 0  # ARRIVE-VIA followed by ERROR QUEUE-FULL
    incomplete: int = 0  # arrived but never exited a server before the log ended
    orphan_exits: int = 0  # EXITS-SERVER with no matching ARRIVE-VIA
    queue_ids: set[str] = field(default_factory=set)


def iter_visit_rows(
    events: Iterable[Event],
    summary: Summary | None = None,
    warn: Warn | None = None,
) -> Iterator[VisitRow]:
    """Yield one VisitRow per completed visit, in the order visits complete.

    Streaming: only visits currently inside a queue are held in memory, so the
    tool scales to large Obj F logs.
    """
    summary = summary if summary is not None else Summary()
    open_visits: dict[tuple[str, str], OpenVisit] = {}

    for event in events:
        summary.queue_ids.add(event.qsid)
        key = (event.job, event.qsid)

        if event.kind == "ARRIVE-VIA":
            if key in open_visits:
                summary.incomplete += 1
                if warn:
                    warn(
                        f"t={event.time}: {event.job} re-arrived in {event.qsid} before "
                        "exiting a server; previous visit discarded"
                    )
            open_visits[key] = OpenVisit(arrival=event.time)

        elif event.kind in ("ENTERS-SERVER", "TASK-START"):
            visit = open_visits.get(key)
            if visit is not None and visit.entered is None:
                visit.entered = event.time

        elif event.kind == "EXITS-SERVER":
            visit = open_visits.pop(key, None)
            if visit is None:
                summary.orphan_exits += 1
                if warn:
                    warn(f"t={event.time}: {event.job} exited a server in {event.qsid} without arriving")
                continue
            if visit.entered is None:
                # No ENTERS-SERVER/TASK-START line seen; treat service as instantaneous.
                visit.entered = event.time
                if warn:
                    warn(f"t={event.time}: {event.job} in {event.qsid} exited without ENTERS-SERVER")
            summary.visits += 1
            yield VisitRow(event.job, event.qsid, visit.arrival, visit.entered, event.time)

        elif event.kind == "DEPART-VIA":
            # Normally EXITS-SERVER already closed the visit. Older logs that skip
            # EXITS-SERVER can still be handled by closing on departure.
            visit = open_visits.pop(key, None)
            if visit is not None:
                if visit.entered is None:
                    summary.incomplete += 1
                else:
                    summary.visits += 1
                    yield VisitRow(event.job, event.qsid, visit.arrival, visit.entered, event.time)

        elif event.kind == "ERROR":
            if event.rest.split()[:1] == ["QUEUE-FULL"]:
                if open_visits.pop(key, None) is not None:
                    summary.dropped += 1
            # NO-OUT-EDGE happens after EXITS-SERVER; nothing is open for it.

    summary.incomplete += len(open_visits)


def derive_event_metrics(
    lines: Iterable[str],
    summary: Summary | None = None,
    warn: Warn | None = None,
) -> list[VisitRow]:
    """Convenience wrapper for in-memory logs (tests): lines -> rows."""
    return list(iter_visit_rows(iter_events(lines, warn), summary, warn))


def write_rows(rows: Iterable[VisitRow], out: TextIO) -> None:
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow(row.as_csv())


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive per-visit job metrics (queue wait, service, turnaround) from a simulator event log."
    )
    parser.add_argument("--events", required=True, help="Path to the event log (job.log / events.log)")
    parser.add_argument("--out", default="-", help="Output CSV path (default: '-' = stdout)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print a summary to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def warn(message: str) -> None:
        print(f"derive-event-metrics: {message}", file=sys.stderr)

    summary = Summary()
    try:
        with open(args.events, encoding="utf-8") as fh:
            rows = iter_visit_rows(iter_events(fh, warn), summary, warn if args.verbose else None)
            if args.out == "-":
                write_rows(rows, sys.stdout)
            else:
                with open(args.out, "w", encoding="utf-8", newline="") as out:
                    write_rows(rows, out)
    except OSError as exc:
        raise SystemExit(f"derive-event-metrics: cannot read {args.events}: {exc}") from exc

    if summary.dropped:
        warn(f"{summary.dropped} visit(s) rejected with QUEUE-FULL (no row emitted)")
    if summary.incomplete:
        warn(f"{summary.incomplete} visit(s) never completed before the log ended (no row emitted)")
    if summary.orphan_exits:
        warn(f"{summary.orphan_exits} EXITS-SERVER line(s) had no matching arrival")
    if args.verbose:
        print(
            f"derive-event-metrics: queues={sorted(summary.queue_ids)} visits={summary.visits} "
            f"dropped={summary.dropped} incomplete={summary.incomplete}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create a Gantt-style job lifecycle trace from a simulator event log.

The Objective B/E event log grammar is::

    <time> <job-id> IN <queue-system-id> <event-type> [details...]

One horizontal lifeline is drawn per job.  Selected lifecycle events are
overlaid as markers, including every queue visit made by a job.

Usage::

    python create_event_trace.py --events events.log [--limit N]
                                 [--out etrace.png]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


Warn = Callable[[str], None]


@dataclass(frozen=True)
class Event:
    """The fields needed from one simulator event-log line."""

    time: int
    job: str
    qsid: str
    kind: str
    details: str = ""


# Marker names match event tokens emitted by simulator. A job can have
# several markers of same kind when moving through several queues
MARKERS = {
    "ARRIVE-VIA": {"marker": "o", "color": "#2a78d6", "label": "Arrive via"},
    "TASK-START": {"marker": "^", "color": "#ed7d31", "label": "Task start"},
    "EXITS-SERVER": {"marker": "s", "color": "#2e9b57", "label": "Exits server"},
    "DEPART-VIA": {"marker": "*", "color": "#8856a7", "label": "Depart via"},
}


def parse_event(line: str) -> Event | None:
    """Parse one event-log line, returning ``None`` for malformed input."""

    parts = line.split(maxsplit=5)
    if len(parts) < 5 or parts[2] != "IN":
        return None
    try:
        time = int(parts[0])
    except ValueError:
        return None
    details = parts[5].strip() if len(parts) > 5 else ""
    return Event(time, parts[1], parts[3], parts[4], details)


def iter_events(lines: Iterable[str], warn: Warn | None = None) -> Iterator[Event]:
    """Yield valid events; optionally reports skipped nonblank lines."""

    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        event = parse_event(line)
        if event is None:
            if warn is not None:
                warn(f"line {lineno}: not an event line, skipped: {line.rstrip()}")
            continue
        yield event


def first_jobs(events: Sequence[Event], limit: int | None = None) -> list[str]:
    """Return job IDs in first-appearance order, optionally capped at ``limit``."""

    jobs: list[str] = []
    seen: set[str] = set()
    for event in events:
        if event.job in seen:
            continue
        seen.add(event.job)
        jobs.append(event.job)
        if limit is not None and len(jobs) == limit:
            break
    return jobs


def plot_event_trace(events: Sequence[Event], out: str | Path, limit: int | None = None) -> int:
    """Plot selected jobs and return the number of job lifelines drawn."""

    jobs = first_jobs(events, limit)
    if not jobs:
        raise ValueError("event log contains no valid events")

    selected = set(jobs)
    selected_events = [event for event in events if event.job in selected]
    y_positions = {job: y for y, job in enumerate(jobs)}

    bounds: dict[str, list[int]] = {}
    for event in selected_events:
        if event.job not in bounds:
            bounds[event.job] = [event.time, event.time]
        else:
            bounds[event.job][0] = min(bounds[event.job][0], event.time)
            bounds[event.job][1] = max(bounds[event.job][1], event.time)

    # Some math here; grow the figure height for more jobs but not too much
    # min height = 3.5, max height = 16.0, base height = 1.0, growth factor = 0.55
    height = min(16.0, max(3.5, 1.0 + 0.55 * len(jobs)))
    fig, ax = plt.subplots(figsize=(11, height))

    for job in jobs:
        start, end = bounds[job]
        y = y_positions[job]
        ax.plot([start, end], [y, y], color="#9a9a94", linewidth=1.5, zorder=1)

    for kind, style in MARKERS.items():
        matching = [event for event in selected_events if event.kind == kind]
        if not matching:
            continue
        ax.scatter(
            [event.time for event in matching],
            [y_positions[event.job] for event in matching],
            marker=style["marker"],
            color=style["color"],
            edgecolors="white",
            linewidths=0.6,
            s=95 if kind != "DEPART-VIA" else 140,
            zorder=2,
        )

    ax.set_yticks(range(len(jobs)), labels=jobs)
    ax.invert_yaxis()  # First job in the log appears at top
    ax.set_xlabel("Time step")
    ax.set_ylabel("Job ID")
    ax.set_title("Event Trace Plot: Job Lifecycle", loc="left")
    ax.grid(axis="x", color="#deddd7", linestyle="--", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    present_kinds = {event.kind for event in selected_events}
    legend_handles = [
        Line2D(
            [],
            [],
            linestyle="None",
            marker=style["marker"],
            markerfacecolor=style["color"],
            markeredgecolor="white",
            markersize=9 if kind != "DEPART-VIA" else 11,
            label=style["label"],
        )
        for kind, style in MARKERS.items()
        if kind in present_kinds
    ]
    if legend_handles:
        ax.legend(handles=legend_handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)

    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return len(jobs)


def positive_int(value: str) -> int:
    """Argparse type for a strictly positive job limit."""

    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Gantt-style job lifecycle trace from a simulator event log."
    )
    parser.add_argument("--events", required=True, help="Path to events.log")
    parser.add_argument("--limit", type=positive_int, default=None, help="Plot only the first N jobs")
    parser.add_argument("--out", default="etrace.png", help="Output image path (default: etrace.png)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Report skipped lines and plot counts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def warn(message: str) -> None:
        print(f"create-event-trace: {message}", file=sys.stderr)

    try:
        with open(args.events, encoding="utf-8") as event_file:
            events = list(iter_events(event_file, warn if args.verbose else None))
        jobs_plotted = plot_event_trace(events, args.out, args.limit)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"create-event-trace: {exc}") from exc

    if args.verbose:
        selected_jobs = set(first_jobs(events, args.limit))
        marker_count = sum(
            event.job in selected_jobs and event.kind in MARKERS for event in events
        )
        warn(
            f"jobs={jobs_plotted} parsed-events={len(events)} "
            f"lifecycle-markers={marker_count} output={args.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

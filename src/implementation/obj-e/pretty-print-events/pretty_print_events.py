#!/usr/bin/env python3
"""Place each queue's events in its own column, colored by event type.

The layout follows the dslogs pretty-printer: columns are horizontal offsets,
not a ruled table. A clock with several events uses extra rows, and the time
is printed only on the first of those rows.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
LINE_RE = re.compile(r"^(\d+)\s+(\S+)\s+IN\s+(\S+)\s+(\S+)(?:\s+(.*))?$")
QUEUE_NUM = re.compile(r"^q(\d+)$")

RESET = "\033[0m"
COLORS = {
    "ARRIVE-VIA": "\033[96m",
    "DEPART-VIA": "\033[95m",
    "ENTERS-SERVER": "\033[93m",
    "EXITS-SERVER": "\033[33m",
    "TASK-START": "\033[92m",
    "TASK-END": "\033[32m",
    "ERROR": "\033[1;91m",
}


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def queue_sort_key(qid: str) -> tuple:
    match = QUEUE_NUM.match(qid)
    if match:
        return (0, int(match.group(1)), qid)
    return (1, 0, qid)


def paint(text: str, event: str | None, use_color: bool) -> str:
    if not text or not use_color or not event:
        return text
    code = COLORS.get(event, "")
    if not code:
        return text
    return f"{code}{text}{RESET}"


def wrap_words(text: str, width: int) -> list[str]:
    if len(text) <= width:
        return [text]
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def message(qid: str, job_id: str, event: str, details: str) -> str:
    text = f"{qid} {job_id} {event}"
    if details:
        text = f"{text} {details}"
    return text


def parse_lines(lines: list[str]) -> tuple[dict[int, dict[str, list[str]]], list[str]]:
    """Return time -> queue -> plain event strings, and the sorted queue ids."""
    grouped: dict[int, dict[str, list[tuple[str, str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    queues: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LINE_RE.match(line)
        if not match:
            print(f"skipping unrecognized line: {line}", file=sys.stderr)
            continue
        clock = int(match.group(1))
        job_id, qsid, event = match.group(2), match.group(3), match.group(4)
        details = (match.group(5) or "").strip()
        grouped[clock][qsid].append((job_id, event, details))
        queues.add(qsid)
    ordered = sorted(queues, key=queue_sort_key)
    return grouped, ordered


def column_width(grouped: dict, queues: list[str]) -> int:
    # Wide enough for the longest event, so ARRIVE-VIA / TASK-START / TASK-END stay on one line.
    widest = 0
    for by_q in grouped.values():
        for qid in queues:
            for job_id, event, details in by_q.get(qid, []):
                widest = max(widest, len(message(qid, job_id, event, details)))
    return max(widest, 1)


def render(grouped: dict, queues: list[str], use_color: bool) -> list[str]:
    time_width = max((len(str(clock)) for clock in grouped), default=1)
    col_width = column_width(grouped, queues)
    out: list[str] = []
    for clock in sorted(grouped):
        by_q = grouped[clock]
        height = max((len(by_q.get(qid, [])) for qid in queues), default=0)
        for row in range(height):
            wrapped: list[tuple[list[str], str | None]] = []
            for qid in queues:
                events = by_q.get(qid, [])
                if row < len(events):
                    job_id, event, details = events[row]
                    wrapped.append((wrap_words(message(qid, job_id, event, details), col_width), event))
                else:
                    wrapped.append(([""], None))
            depth = max(len(parts) for parts, _event in wrapped)
            for line_i in range(depth):
                stamp = str(clock) if row == 0 and line_i == 0 else ""
                chunks = [stamp.rjust(time_width)]
                for parts, event in wrapped:
                    piece = parts[line_i] if line_i < len(parts) else ""
                    padded = piece.ljust(col_width)
                    chunks.append(paint(padded, event if piece else None, use_color))
                out.append(" ".join(chunks).rstrip())
    return out


def read_events(path: str | None) -> list[str]:
    if path is None:
        if sys.stdin.isatty():
            fallback = Path("events.log")
            if not fallback.is_file():
                print("pass an event log, or pipe one on stdin", file=sys.stderr)
                raise SystemExit(2)
            return fallback.read_text(encoding="utf-8").splitlines()
        return sys.stdin.read().splitlines()
    source = Path(path)
    if not source.is_file():
        print(f"event log not found: {source}", file=sys.stderr)
        raise SystemExit(2)
    return source.read_text(encoding="utf-8").splitlines()


def show(lines: list[str], use_color: bool) -> None:
    text = "\n".join(lines) + "\n"
    if not use_color or not sys.stdout.isatty() or shutil.which("less") is None:
        sys.stdout.write(text)
        return
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".log") as tmp:
        tmp.write(text)
        name = tmp.name
    try:
        subprocess.run(["less", "-R", name], check=False)
    except (OSError, KeyboardInterrupt):
        sys.stdout.write(text)
    finally:
        Path(name).unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a queue-column view of a simulator event log."
    )
    parser.add_argument(
        "event_log",
        nargs="?",
        help="Event log path. Omit to read events.log or stdin.",
    )
    parser.add_argument(
        "--out",
        help="Write a .log instead of the terminal. Color codes stay unless --no-color is set.",
    )
    parser.add_argument("--no-color", action="store_true", help="Do not emit ANSI color")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    grouped, queues = parse_lines(read_events(args.event_log))
    if not queues:
        print("no events", file=sys.stderr)
        return 1
    use_color = not args.no_color
    lines = render(grouped, queues, use_color)
    if args.out:
        text = "\n".join(lines if use_color else [strip_ansi(line) for line in lines]) + "\n"
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {Path(args.out).resolve()}")
        return 0
    show(lines, use_color)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

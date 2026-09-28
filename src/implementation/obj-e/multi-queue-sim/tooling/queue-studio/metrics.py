"""Hooks for Obj C analysis and the remaining Obj E tools.

pretty-print-events runs the implementation next to the simulator. The other
entries name a future path and raise NotImplementedError.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetricTool:
    objective: str
    name: str
    future_path: str
    consumes: str
    purpose: str


CATALOG: list[MetricTool] = [
    MetricTool("Obj C", "filter-by-queue", "src/implementation/obj-c/filter-by-queue", "qmet", "Keep qmet rows for selected queue ids."),
    MetricTool("Obj C", "filter-by-job", "src/implementation/obj-c/filter-by-job", "events", "Keep event lines for selected job ids."),
    MetricTool("Obj C", "compute-use", "src/implementation/obj-c/compute-use", "qmet", "Utilization, saturation, and errors over time windows."),
    MetricTool("Obj C", "plot-use", "src/implementation/obj-c/plot-use", "quse csv", "Plot USE series."),
    MetricTool("Obj C", "derive-sys-metrics", "src/implementation/obj-c/derive-sys-metrics", "qmet", "Queue length and related system metrics."),
    MetricTool("Obj C", "plot-sys-metrics", "src/implementation/obj-c/plot-sys-metrics", "sysmetrics csv", "Plot system metrics."),
    MetricTool("Obj C", "derive-event-metrics", "src/implementation/obj-c/derive-event-metrics", "events", "Response and service times from the event log."),
    MetricTool("Obj C", "plot-event-metrics", "src/implementation/obj-c/plot-derive-event-metrics", "emetrics csv", "Plot event-derived metrics."),
    MetricTool("Obj C", "create-event-trace", "src/implementation/obj-c/create-event-trace", "events", "Gantt-style trace of job movement."),
    MetricTool("Obj E", "pretty-print-events", "src/implementation/obj-e/pretty-print-events", "events", "Aligned terminal view of the event log."),
    MetricTool("Obj E", "create-config-from-network", "src/implementation/obj-e/create-config-from-network", "network matrix", "Build qconf.csv from a network description."),
]


def _pretty_print(events: Path) -> None:
    script = (
        Path(__file__).resolve().parents[3]
        / "pretty-print-events"
        / "pretty_print_events.py"
    )
    subprocess.run([sys.executable, str(script), str(events)], check=True)


def run(tool: MetricTool, artifacts: dict[str, Path] | None) -> None:
    events = artifacts.get("events") if artifacts else None
    if tool.name == "pretty-print-events" and events is not None and Path(events).is_file():
        _pretty_print(Path(events))
        return
    available = "none yet"
    if artifacts:
        present = [name for name in ("qmet", "events", "workload", "config", "sink") if Path(artifacts[name]).is_file()]
        available = ", ".join(present) if present else "none yet"
    raise NotImplementedError(
        f"{tool.name} is not implemented.\n"
        f"    purpose: {tool.purpose}\n"
        f"    will read: {tool.consumes}\n"
        f"    future path: {tool.future_path}\n"
        f"    artifacts on disk now: {available}"
    )

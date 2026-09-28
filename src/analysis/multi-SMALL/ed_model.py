#!/usr/bin/env python3
"""Emergency-department (ED) patient-flow model for Queue Lab Objective F (SMALL).

The real-world process: a hospital emergency department. Patients register,
get triaged, and are routed to a fast-track area, one of two treatment pods,
or straight to diagnostics (lab / X-ray / CT) that were ordered at triage.
Treated patients go through disposition and leave either by discharge or by
admission to the hospital.

Mapping to the simulator (Obj B / Obj E engine):

* one **time step = 10 minutes**
* a **job** is a patient; its task list is the list of care steps the patient
  needs, each with a work value W = units of staff attention (1 unit ~ 10 min)
* a **queue system** is a station (registration desk, triage, pod, lab, ...);
  its servers are the clerks / nurses / beds / machines at that station
* a station with a bare ``Sub-X`` does X units of attention per visit and hands
  the patient on; a station with ``Sub-X*`` keeps the patient until all of the
  remaining care is done
* ``Queue Max Size`` is the waiting room / hallway capacity at that station;
  a patient who cannot fit is turned away (``ERROR QUEUE-FULL``) which is the
  ED's "left without being seen" / ambulance-diversion outcome
* sinks are the two ways out of the ED: ``out_discharge.wl`` and ``out_admit.wl``

Routing note. The simulator picks an outgoing edge with a deterministic
weighted round-robin whose block length equals the integerised weight
(weight x 1000). A weight of ``1.0`` therefore sends 1000 consecutive patients
down the same edge before switching. To get an interleaved split we encode
weights as *slot counts* divided by 1000: ``q2:0.004,q3:0.002`` means "4 to
q2, then 2 to q3, repeat".
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

STEP_MINUTES = 10  # one simulator time step

CONFIG_HEADER = (
    "Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,"
    "Source,Sink,Edges in,Edges out"
)


@dataclass(frozen=True)
class Station:
    """One queue system of the ED network."""

    id: str
    name: str
    group: str  # intake / treatment / diagnostics / exit (used for plot colors)
    servers: int
    sub: int  # X in Sub-X: units of attention delivered per rate window
    repeat: bool  # True -> Sub-X* (stay until all care is done)
    rate: int  # time steps per application of Sub-X
    max_size: int  # waiting capacity (patients), not counting those in service
    edges: tuple[tuple[str, int], ...] = ()  # (target id, routing slots)
    source: str | None = None  # workload file name (only the entrance)
    sink: str | None = None  # sink file name (only the exits)

    @property
    def server_function(self) -> str:
        return f"Sub-{self.sub}{'*' if self.repeat else ''}"

    @property
    def servers_label(self) -> str:
        return {"registration": "clerks", "triage": "nurses", "fast_track": "providers",
                "pod_a": "beds", "pod_b": "beds", "lab": "analyzers", "xray": "machines",
                "ct": "scanners", "disposition": "physicians", "discharge": "nurses",
                "admit": "boarding beds"}.get(self.name, "servers")


# --------------------------------------------------------------------------- #
# Baseline network (11 stations). Rates are in 10-minute steps.
# --------------------------------------------------------------------------- #
BASELINE: tuple[Station, ...] = (
    Station("q0", "registration", "intake", servers=3, sub=1, repeat=False, rate=1, max_size=30,
            edges=(("q1", 1),), source="arrivals.wl"),
    Station("q1", "triage", "intake", servers=3, sub=1, repeat=False, rate=1, max_size=20,
            # fast-track 4 : pod A 2 : pod B 2 : lab 1 : X-ray 1 : CT 1  (of every 11)
            edges=(("q2", 4), ("q3", 2), ("q4", 2), ("q5", 1), ("q6", 1), ("q7", 1))),
    Station("q2", "fast_track", "treatment", servers=2, sub=3, repeat=True, rate=1, max_size=15,
            edges=(("q9", 1),)),
    Station("q3", "pod_a", "treatment", servers=3, sub=2, repeat=True, rate=2, max_size=6,
            edges=(("q8", 1),)),
    Station("q4", "pod_b", "treatment", servers=3, sub=2, repeat=True, rate=2, max_size=6,
            edges=(("q8", 1),)),
    Station("q5", "lab", "diagnostics", servers=1, sub=1, repeat=False, rate=4, max_size=20,
            edges=(("q3", 1), ("q4", 1))),
    Station("q6", "xray", "diagnostics", servers=1, sub=1, repeat=False, rate=2, max_size=10,
            edges=(("q3", 1), ("q4", 1))),
    Station("q7", "ct", "diagnostics", servers=1, sub=1, repeat=False, rate=3, max_size=10,
            edges=(("q3", 1), ("q4", 1))),
    Station("q8", "disposition", "exit", servers=2, sub=1, repeat=False, rate=1, max_size=20,
            # discharge 4 : admit 1
            edges=(("q9", 4), ("q10", 1))),
    Station("q9", "discharge", "exit", servers=3, sub=3, repeat=True, rate=1, max_size=20,
            sink="out_discharge.wl"),
    Station("q10", "admit", "exit", servers=2, sub=3, repeat=True, rate=6, max_size=6,
            sink="out_admit.wl"),
)

GROUP_ORDER = ("intake", "treatment", "diagnostics", "exit")


def station_map(stations: tuple[Station, ...]) -> dict[str, Station]:
    return {s.id: s for s in stations}


def numeric_id(qid: str) -> int:
    """q7 -> 7 (qmet.csv reports the numeric id)."""
    return int("".join(ch for ch in qid if ch.isdigit()) or 0)


# --------------------------------------------------------------------------- #
# Scenario transforms
# --------------------------------------------------------------------------- #
def _scaled_int(value: int, factor: float) -> int:
    """Round half up, never below 1 (a station cannot have zero servers)."""
    return max(1, int(value * factor + 0.5))


def scale_servers(stations: tuple[Station, ...], factor: float) -> tuple[Station, ...]:
    """Scale every station's server count by ``factor``, rounding half up per station.

    Simple, but with 1-3 servers per station a -10% cut rounds back to the
    original counts. The sensitivity study therefore uses
    :func:`scale_servers_total`, which hits the requested total exactly.
    """
    return tuple(replace(s, servers=_scaled_int(s.servers, factor)) for s in stations)


def scale_servers_total(stations: tuple[Station, ...], factor: float) -> tuple[Station, ...]:
    """Scale the *total* number of servers by ``factor`` (largest-remainder apportionment).

    target = round(total * factor). Each station first gets floor(servers * factor)
    (never below 1). The remaining servers go one each to the stations with the
    largest fractional remainder; ties go to the station with fewer servers
    (where one server is the biggest relative change), then to config order.
    If the floors already exceed the target (many 1-server stations), servers
    are removed from the largest stations first, never below 1.
    """
    total = total_servers(stations)
    target = max(len(stations), int(total * factor + 0.5))
    exact = [s.servers * factor for s in stations]
    counts = [max(1, int(e)) for e in exact]
    remainders = [e - int(e) if int(e) >= 1 else 0.0 for e in exact]
    leftover = target - sum(counts)
    if leftover > 0:
        order = sorted(range(len(stations)), key=lambda i: (-remainders[i], stations[i].servers, i))
        for i in order[:leftover]:
            counts[i] += 1
    elif leftover < 0:
        order = sorted(range(len(stations)), key=lambda i: (-counts[i], i))
        for i in order:
            if leftover == 0:
                break
            if counts[i] > 1:
                counts[i] -= 1
                leftover += 1
    return tuple(replace(s, servers=c) for s, c in zip(stations, counts))


def scale_queue_depth(stations: tuple[Station, ...], factor: float) -> tuple[Station, ...]:
    """Uniformly scale waiting capacity at every station."""
    return tuple(replace(s, max_size=_scaled_int(s.max_size, factor)) for s in stations)


def add_servers(stations: tuple[Station, ...], extra: dict[str, int]) -> tuple[Station, ...]:
    """Targeted change: add servers at specific stations only."""
    return tuple(replace(s, servers=s.servers + extra.get(s.id, 0)) for s in stations)


def pool_pods(stations: tuple[Station, ...]) -> tuple[Station, ...]:
    """Topology change: merge pod A and pod B into one pooled pod with all beds.

    Every edge that pointed at pod B is redirected to pod A, and pod A gets
    pod B's beds and waiting capacity. Pod B is removed from the network.
    """
    by_id = station_map(stations)
    pod_a, pod_b = by_id["q3"], by_id["q4"]
    pooled = replace(pod_a, name="pooled_pod", servers=pod_a.servers + pod_b.servers,
                     max_size=pod_a.max_size + pod_b.max_size)
    out: list[Station] = []
    for s in stations:
        if s.id == "q4":
            continue
        if s.id == "q3":
            out.append(pooled)
            continue
        merged: dict[str, int] = {}
        for target, slots in s.edges:
            target = "q3" if target == "q4" else target
            merged[target] = merged.get(target, 0) + slots
        out.append(replace(s, edges=tuple(merged.items())))
    return tuple(out)


def total_servers(stations: tuple[Station, ...]) -> int:
    return sum(s.servers for s in stations)


# --------------------------------------------------------------------------- #
# Config / workload writers
# --------------------------------------------------------------------------- #
def edges_in(stations: tuple[Station, ...], qid: str) -> list[str]:
    return [s.id for s in stations if any(t == qid for t, _ in s.edges)]


def write_config(stations: tuple[Station, ...], path: Path, workload: Path, run_dir: Path) -> None:
    """Write qconf.csv.

    Source/sink paths are written exactly as given (the driver passes paths
    relative to the ``multi-SMALL/`` directory and runs the simulator from
    there), so the committed configs work on any machine.
    """
    rows = [CONFIG_HEADER]
    for s in stations:
        source = workload.as_posix() if s.source else ""
        sink = (run_dir / s.sink).as_posix() if s.sink else ""
        ein = "[" + ",".join(edges_in(stations, s.id)) + "]"
        eout = "[" + ",".join(f"{t}:{slots / 1000:.3f}" for t, slots in s.edges) + "]"
        rows.append(
            f"{s.id},{s.max_size},{s.servers},{s.server_function},{s.rate},{source},{sink},{ein},{eout}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_station_table(stations: tuple[Station, ...], path: Path) -> None:
    """Human-readable station table (Markdown) next to the config."""
    lines = [
        "| id | station | group | servers | function | rate (steps) | waiting cap | routes to (slots) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in stations:
        routes = ", ".join(f"{t}:{n}" for t, n in s.edges) if s.edges else f"sink `{s.sink}`"
        lines.append(
            f"| {s.id} | {s.name} | {s.group} | {s.servers} {s.servers_label} | `{s.server_function}` | "
            f"{s.rate} | {s.max_size} | {routes} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rescale_arrivals(src: Path, dst: Path, factor: float) -> int:
    """Copy a workload, multiplying every arrival time by ``factor``.

    Keeps the patient mix (tasks / work) identical while changing the arrival
    rate: factor 0.5 halves the load (arrivals spread over twice the time),
    factor 1.5 packs the same patients into two thirds of the time. Sorted
    order is preserved because the map is monotone.
    """
    with open(src, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    with open(dst, "w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(header)
        for job_id, arrival, tasks in rows:
            writer.writerow([job_id, int(int(arrival) * factor), tasks])
    return len(rows)


def stations_to_json(stations: tuple[Station, ...]) -> str:
    return json.dumps([s.__dict__ for s in stations], indent=2, default=list)


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    study: str  # scale | load | servers | targeted
    stations: tuple[Station, ...]
    interval: str  # generator interval for the base stream
    rate_factor: float = 1.0  # arrival-time compression (1.5 = 50% more load)
    seed: int = 4113
    level: float | None = None  # x position in sensitivity plots (e.g. -0.3, +0.25)
    notes: str = ""
    extra_plots: bool = False  # full plot set (baseline) vs compact set


def build_scenarios() -> dict[str, Scenario]:
    base = BASELINE
    scenarios = [
        # --- scale: same arrival rate, more patients (longer horizon) ---------- #
        Scenario("scale-1k", "1,000 patients (~3.5 days)", "scale", base, "0:499", level=1000),
        Scenario("base-3k", "3,000 patients (~10 days), baseline", "scale", base, "0:1499", level=3000,
                 extra_plots=True),
        Scenario("scale-10k", "10,000 patients (~35 days)", "scale", base, "0:4999", level=10000),
        # --- load: same 3k patient stream, arrival rate x0.5 / x1.5 ------------ #
        Scenario("load-quiet", "Quiet: half the arrival rate", "load", base, "0:1499", rate_factor=0.5, level=0.5),
        Scenario("load-surge", "Surge: 1.5x the arrival rate", "load", base, "0:1499", rate_factor=1.5, level=1.5),
        # --- sensitivity: +/- total servers, apportioned across stations -------- #
        Scenario("srv-30", "-30% servers", "servers", scale_servers_total(base, 0.7), "0:1499", level=-0.30),
        Scenario("srv-20", "-20% servers", "servers", scale_servers_total(base, 0.8), "0:1499", level=-0.20),
        Scenario("srv-10", "-10% servers", "servers", scale_servers_total(base, 0.9), "0:1499", level=-0.10),
        Scenario("srv+25", "+25% servers", "servers", scale_servers_total(base, 1.25), "0:1499", level=0.25),
        Scenario("srv+50", "+50% servers", "servers", scale_servers_total(base, 1.5), "0:1499", level=0.50),
        Scenario("srv+100", "+100% servers", "servers", scale_servers_total(base, 2.0), "0:1499", level=1.00),
        # --- targeted alternatives ---------------------------------------------- #
        Scenario("lab+1", "+1 lab analyzer only", "targeted", add_servers(base, {"q5": 1}), "0:1499",
                 notes="one extra server at the station with the highest utilization"),
        Scenario("pods+1", "+1 bed in each pod only", "targeted", add_servers(base, {"q3": 1, "q4": 1}), "0:1499",
                 notes="two extra servers (+8%) at the stations with the longest waits"),
        Scenario("pooled-pods", "Pods A+B pooled into one 6-bed pod", "targeted", pool_pods(base), "0:1499",
                 notes="topology / link change, same total beds"),
        Scenario("depth-50", "-50% waiting capacity everywhere", "targeted", scale_queue_depth(base, 0.5), "0:1499",
                 notes="queue depth as the resource"),
    ]
    return {s.name: s for s in scenarios}


if __name__ == "__main__":
    # Quick self-check: print the baseline table.
    for s in BASELINE:
        print(f"{s.id:>4} {s.name:<13} {s.servers:>2} x {s.server_function:<7} rate={s.rate} cap={s.max_size} -> {s.edges or s.sink}")
    print("total servers:", total_servers(BASELINE))
    for f in (0.7, 0.8, 0.9, 1.25, 1.5, 2.0):
        scaled = scale_servers_total(BASELINE, f)
        print(f"factor {f}: {[st.servers for st in scaled]} total={total_servers(scaled)}")

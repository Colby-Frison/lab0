#!/usr/bin/env python3
"""Internet AS-level packet-forwarding model for Queue Lab Objective F (LARGE).

The real-world process: packets crossing the Internet between Autonomous
Systems (ASes). The graph is the SNAP ``as-733`` snapshot ``as20000102.txt``
(6,474 ASes, 12,572 links after dropping self-loops).

Mapping to the simulator (Obj B / Obj E engine):

* a **queue system** is an AS; its servers are its forwarding capacity
  (``servers = max(1, ceil(degree / k))``, ``Sub-1`` at rate 1)
* a **job** is a packet with one task ``W 4``: every AS visit removes one unit,
  so a packet is done after 4 visits (its AS path length)
* **every AS** has its own sink: a packet leaves where its 4th visit ends, so
  every delivered packet crosses exactly 4 ASes. (With sinks on stubs only,
  done packets kept wandering until they reached a stub: 14 visits on average.)
* a seeded sample of **stub ASes** (degree 1, edge networks) are the sources
* ``Queue Max Size`` is the AS's buffer; overflow is ``ERROR QUEUE-FULL``
  = packet loss
* every link is an edge in both directions with weight ``0.001``

Routing note. The simulator picks an outgoing edge with a deterministic
weighted round-robin in blocks of weight x 1000, so weight ``1.0`` would send
1000 consecutive packets down one link. Weight ``0.001`` (one slot per link)
makes an AS alternate between its links.

Graph parsing and config rows come from the Obj E ``create-config-network``
tool; packet streams come from the Obj A workload generator.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src/implementation/obj-e/create-config-network"))
sys.path.insert(0, str(REPO / "src/implementation/obj-a/workload-generator"))

import create_config_from_network as ccn  # noqa: E402
import workload_generator as wg  # noqa: E402

GRAPH = HERE / "as20000102.txt"
EDGE_WEIGHT = 0.001  # one round-robin slot per link
HOPS = 4  # work units per packet = AS visits until done
NUM_SOURCES = 500
SEED = 7
# k in servers = max(1, ceil(degree / k)). The pilot showed ~0.01 busy servers per
# link at 20 packets/step, so k = 70 puts the hubs at about 70% utilization.
DEGREE_PER_SERVER = 70
MIN_QUEUE = 8


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #
def load_graph(path: Path = GRAPH) -> ccn.Network:
    """Parse the SNAP edge list, mirror every link, drop self-loops, weight 0.001."""
    with open(path, encoding="utf-8") as fh:
        net = ccn.parse_network(fh, undirected=True, ignore_weights=True)
    edges = tuple(
        ccn.Edge(e.source, e.target, EDGE_WEIGHT) for e in net.edges if e.source != e.target
    )
    return ccn.Network(net.nodes, edges)


def degrees(net: ccn.Network) -> dict[str, int]:
    counts = Counter(e.source for e in net.edges)
    return {node: counts.get(node, 0) for node in net.nodes}


def stubs(net: ccn.Network) -> list[str]:
    """Degree-1 ASes, in network node order."""
    deg = degrees(net)
    return [node for node in net.nodes if deg[node] == 1]


def pick_sources(stub_nodes: list[str], n: int = NUM_SOURCES, seed: int = SEED) -> list[str]:
    """A seeded sample of stubs that send traffic, in network node order."""
    chosen = set(random.Random(seed).sample(stub_nodes, n))
    return [node for node in stub_nodes if node in chosen]


def queue_ids(net: ccn.Network) -> dict[str, str]:
    """Original AS number -> queue id (same numbering as build_config_rows)."""
    return {node: f"q{i}" for i, node in enumerate(net.nodes)}


# --------------------------------------------------------------------------- #
# Servers
# --------------------------------------------------------------------------- #
def servers_from_degree(deg: dict[str, int], k: int = DEGREE_PER_SERVER) -> dict[str, int]:
    return {node: max(1, math.ceil(d / k)) for node, d in deg.items()}


def scale_servers_total(servers: dict[str, int], factor: float) -> dict[str, int]:
    """Scale servers by ``factor``, aiming at ``factor`` x the total (min 1 per AS).

    Increases reach the target total exactly (largest-remainder rounding).
    Decreases cannot: every AS is first cut to ``floor(servers x factor)`` (at
    least 1), then each multi-server AS loses at most one more server. With
    k = 70 only 28 ASes have more than one server and the rest are pinned at 1,
    so a 0.9 / 0.8 / 0.7 factor cuts each multi-server AS by about 10 / 20 / 30 %
    but the total by under 1 %.
    """
    if factor == 1.0:
        return dict(servers)
    base_total = sum(servers.values())
    target = max(len(servers), round(base_total * factor))
    raw = {node: s * factor for node, s in servers.items()}
    out = {node: max(1, math.floor(v)) for node, v in raw.items()}
    diff = target - sum(out.values())
    if diff > 0:
        order = sorted(raw, key=lambda n: raw[n] - math.floor(raw[n]), reverse=True)
        for node in order[:diff]:
            out[node] += 1
    elif diff < 0:
        order = sorted((n for n in out if out[n] > 1), key=lambda n: raw[n] - out[n])
        for node in order[:-diff]:
            out[node] -= 1
    return out


def queue_size(servers: int) -> int:
    return max(MIN_QUEUE, 4 * servers)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def write_config(
    net: ccn.Network,
    servers: dict[str, int],
    sources: dict[str, str],
    sinks: dict[str, str],
    path: Path,
) -> None:
    """Write qconf.csv; ``sources`` / ``sinks`` map AS number -> workload path."""
    options = ccn.ConfigOptions(
        queue_size=MIN_QUEUE,
        servers=1,
        function="Sub-1",
        rate=1,
        sources=tuple(f"{node}={p}" for node, p in sources.items()),
        sinks=tuple(f"{node}={p}" for node, p in sinks.items()),
        auto_endpoints=False,
    )
    rows, _ = ccn.build_config_rows(net, options)
    for node, row in zip(net.nodes, rows):
        row[1] = str(queue_size(servers[node]))
        row[2] = str(servers[node])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        ccn.write_config(rows, fh)


# --------------------------------------------------------------------------- #
# Workloads
# --------------------------------------------------------------------------- #
def write_workloads(
    sources: list[str],
    qids: dict[str, str],
    total_jobs: int,
    end: int,
    out_dir: Path,
    seed: int = SEED,
) -> dict[str, Path]:
    """One Poisson packet stream per source stub over steps 0..end.

    Uses the Obj A generator in-process. Job ids are renumbered globally so no
    two files share an id. Returns AS number -> workload path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    lam = total_jobs / (len(sources) * (end + 1))
    paths: dict[str, Path] = {}
    next_id = 0
    for i, node in enumerate(sources):
        draw = wg.make_draw("poisson", argparse.Namespace(lam=lam), random.Random(seed + i))
        jobs = wg.generate_jobs(0, end, draw, "fixed", 1, HOPS)
        for job in jobs:
            job["Job Id"] = f"j{next_id}"
            next_id += 1
        path = out_dir / f"in-{qids[node]}.wl"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            wg.write_workload(jobs, fh)
        paths[node] = path
    return paths


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    study: str  # base | scale | servers
    jobs: int
    end: int  # last arrival step; same packets per step at every size
    server_factor: float = 1.0
    level: float | None = None

    @property
    def workload_tag(self) -> str:
        return f"{self.jobs // 1000}k" if self.jobs < 1_000_000 else f"{self.jobs // 1_000_000}m"


BASE_JOBS = 100_000
BASE_END = 4_999  # 100k packets over 5,000 steps = 20 packets per step


def build_scenarios() -> dict[str, Scenario]:
    scenarios = [Scenario("base-100k", "Baseline (100k packets)", "base", BASE_JOBS, BASE_END)]
    for jobs in (300_000, 1_000_000):
        end = (BASE_END + 1) * jobs // BASE_JOBS - 1
        tag = f"{jobs // 1000}k" if jobs < 1_000_000 else "1m"
        scenarios.append(Scenario(f"scale-{tag}", f"Scale: {jobs:,} packets", "scale", jobs, end,
                                  level=float(jobs)))
    for pct in (-10, -20, -30, 25, 50, 100):
        factor = 1 + pct / 100
        scenarios.append(Scenario(f"srv{pct:+d}", f"Servers {pct:+d}%", "servers", BASE_JOBS, BASE_END,
                                  server_factor=factor, level=pct / 100))
    return {sc.name: sc for sc in scenarios}

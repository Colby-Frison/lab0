"""Real communication graph, synthetic work-request model, and controlled scenarios."""

import csv
import hashlib
import io
import gzip
import urllib.request
from dataclasses import dataclass
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 5113
BASE_RATE = 30.0
SOURCE_SHA = "23e0ca0bce21a053025e78f7e9691ac9210ae806a0689bd5edff3c3bac572d4c"


@dataclass(frozen=True)
class Scenario:
    """Inputs for one experiment; load and resource are baseline multipliers."""

    name: str
    study: str
    jobs: int = 30000
    load: float = 1.0
    resource: float = 1.0
    depth: int = 32
    policy: str = "uniform"
    seed: int = SEED


def scenarios():
    """Define the scale, load, server-budget, and targeted experiments."""
    specs = [
        Scenario("base-30k", "scale"),
        Scenario("scale-10k", "scale", 10000),
        Scenario("scale-100k", "scale", 100000),
        Scenario("load-quiet", "load", load=0.5),
        Scenario("load-surge", "load", load=1.5),
    ]
    specs += [
        Scenario(name, "servers", resource=factor)
        for name, factor in [
            ("srv-30", 0.7),
            ("srv-20", 0.8),
            ("srv-10", 0.9),
            ("srv+25", 1.25),
            ("srv+50", 1.5),
            ("srv+100", 2.0),
        ]
    ]
    specs += [
        Scenario("hot+20", "targeted", policy="hot"),
        Scenario("cold+20", "targeted", policy="cold"),
        Scenario("depth-50", "targeted", depth=16),
        Scenario("routing-sorted", "targeted", policy="sorted"),
    ]
    return {s.name: s for s in specs}


def graph():
    """Read the plain-text SNAP edges and return the validated connected core."""
    path = HERE / "data/email-Eu-core.txt"
    if not path.exists():
        url = "https://snap.stanford.edu/data/email-Eu-core.txt.gz"
        with urllib.request.urlopen(url, timeout=60) as response:
            contents = gzip.decompress(response.read())
        assert hashlib.sha256(contents).hexdigest() == SOURCE_SHA
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_SHA
    with path.open("r") as stream:
        network = nx.parse_edgelist(stream, nodetype=int, create_using=nx.DiGraph())
    assert (len(network), network.number_of_edges()) == (1005, 25571)
    network = network.subgraph(
        max(nx.strongly_connected_components(network), key=len)
    ).copy()
    network.remove_edges_from(list(nx.selfloop_edges(network)))
    assert (
        len(network) == 803
        and network.number_of_edges() == 24138
        and nx.is_strongly_connected(network)
    )
    return network


def routing(network, sorted_order=False):
    # Permute once per node with a topology-only seed; same order in every capacity run.
    """Choose a repeatable neighbor order for each node."""
    routes = {}
    for node_id in sorted(network):
        neighbors = sorted(network.successors(node_id))
        if not sorted_order:
            np.random.default_rng(SEED + node_id).shuffle(neighbors)
        routes[node_id] = neighbors
    return routes


def allocation(network, scenario):
    """Assign integer server counts while meeting the scenario resource budget."""
    nodes = sorted(network)
    base = 2 * len(nodes)
    target = int(base * scenario.resource + 0.5)
    exact = 2 * scenario.resource
    counts = {node_id: max(1, int(exact)) for node_id in nodes}
    # Equal fractional remainders: fixed shuffled node order avoids an ID-ranked bias.
    order = np.random.default_rng(SEED).permutation(nodes).tolist()
    for node_id in order[: target - sum(counts.values())]:
        counts[node_id] += 1
    assert sum(counts.values()) == target and min(counts.values()) >= 1
    if scenario.policy in ("hot", "cold"):
        baseline_queues = pd.read_csv(HERE / "results/base-30k/per-queue.csv")
        baseline_queues = baseline_queues.sort_values(
            ["mean_waiting", "queue"], ascending=[scenario.policy == "cold", True]
        )
        for node_id in baseline_queues.head(20)["queue"]:
            counts[int(node_id)] += 1
    return counts


def workload(network, scenario):
    # Separate RNG streams make every shorter workload a true prefix in both times and origins.
    """Generate matched arrivals and source nodes for one scenario."""
    arrival_times = np.cumsum(
        np.random.default_rng(scenario.seed).exponential(1 / BASE_RATE, scenario.jobs)
    )
    origins = np.random.default_rng(scenario.seed + 1).choice(
        sorted(network), scenario.jobs
    )
    return pd.DataFrame(
        {
            "job": [f"j{i}" for i in range(scenario.jobs)],
            "arrival": np.floor(arrival_times / scenario.load).astype(int),
            "source": origins,
        }
    )


def write_inputs(
    network, scenario, counts, routes, jobs, *, root=HERE, check_existing=False
):
    """Write simulator inputs, or compare saved inputs before reanalyzing a run."""

    def save_csv(path, rows):
        stream = io.StringIO(newline="")
        csv.writer(stream).writerows(rows)
        contents = stream.getvalue().encode()
        if check_existing:
            assert (
                path.read_bytes() == contents
            ), f"Input changed: {path}; rerun simulation"
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)

    tag = f"n{scenario.jobs}-load{scenario.load:g}-seed{scenario.seed}"
    workload_dir = root / "workloads" / tag
    grouped = {node_id: source_jobs for node_id, source_jobs in jobs.groupby("source")}
    for node_id in sorted(network):
        rows = [["Job Id", "arrival time", "Tasks"]]
        if node_id in grouped:
            rows.extend(
                (row.job, row.arrival, '["0: W 4"]')
                for row in grouped[node_id].itertuples()
            )
        save_csv(workload_dir / f"in{node_id}.wl", rows)
    run_dir = root / "runs" / scenario.name
    if not check_existing:
        run_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for node_id in sorted(network):
        rows.append(
            [
                f"q{node_id}",
                scenario.depth,
                counts[node_id],
                "Sub-1",
                2,
                str((workload_dir / f"in{node_id}.wl").relative_to(root)),
                f"runs/{scenario.name}/out{node_id}.wl",
                "["
                + ",".join(f"q{x}" for x in sorted(network.predecessors(node_id)))
                + "]",
                "[" + ",".join(f"q{x}:0.001" for x in routes[node_id]) + "]",
            ]
        )
    config_path = root / "configs" / f"{scenario.name}.csv"
    header = [
        "Sys ID",
        "Queue Max Size",
        "Num. Servers",
        "Server Function",
        "Server Function Rate",
        "Source",
        "Sink",
        "Edges in",
        "Edges out",
    ]
    save_csv(config_path, [header, *rows])
    return config_path, run_dir

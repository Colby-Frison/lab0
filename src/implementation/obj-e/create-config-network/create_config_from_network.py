#!/usr/bin/env python3
"""Convert a Matrix Market graph or edge list into a queue config CSV.

Each graph node becomes one queue system. Directed graph edges become the
``Edges in`` and ``Edges out`` fields consumed by simple-queue-sim.

Usage::

    python create_config_from_network.py --network network.mtx --out qconf.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, TextIO


HEADER = [
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


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    weight: float | None = None


@dataclass(frozen=True)
class Network:
    nodes: tuple[str, ...]
    edges: tuple[Edge, ...]


@dataclass(frozen=True)
class ConfigOptions:
    queue_size: int = 8
    servers: int = 1
    function: str = "Sub-10"
    rate: int = 10
    sources: tuple[str, ...] = ()
    sinks: tuple[str, ...] = ()
    auto_endpoints: bool = True


def _number(value: str, context: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{context}: invalid weight {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{context}: weight must be finite")
    return number


def _validate_weight(weight: float | None, context: str, ignore_weights: bool) -> float | None:
    if ignore_weights:
        return None
    if weight is not None and weight <= 0:
        raise ValueError(f"{context}: routing weight must be positive")
    return weight

def nonnegative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return number


def positive_int(value: str) -> int:
    number = nonnegative_int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number

# ------------------------------------------------------------------------------------

def _deduplicate_edges(edges: Iterable[Edge]) -> tuple[Edge, ...]:
    unique: dict[tuple[str, str], Edge] = {}
    for edge in edges:
        key = (edge.source, edge.target)
        previous = unique.get(key)
        if previous is None:
            unique[key] = edge
        elif previous.weight != edge.weight:
            raise ValueError(
                f"edge {edge.source}->{edge.target} appears with conflicting weights "
                f"{previous.weight!r} and {edge.weight!r}"
            )
    return tuple(unique.values())


def _parse_matrix_market(numbered_lines: Sequence[tuple[int, str]], undirected: bool, ignore_weights: bool) -> Network:
    header_lineno, header_line = numbered_lines[0]
    header = header_line.split()
    if len(header) != 5 or header[0].lower() != "%%matrixmarket":
        raise ValueError(f"line {header_lineno}: invalid Matrix Market header")

    _, object_type, storage, field, symmetry = [token.lower() for token in header]
    if object_type != "matrix" or storage != "coordinate":
        raise ValueError("only Matrix Market 'matrix coordinate' files are supported")
    if field not in {"pattern", "integer", "real"}:
        raise ValueError(f"unsupported Matrix Market field: {field}")
    if symmetry not in {"general", "symmetric"}:
        raise ValueError(f"unsupported Matrix Market symmetry: {symmetry}")

    data = [(lineno, line) for lineno, line in numbered_lines[1:] if not line.startswith("%")]
    if not data:
        raise ValueError("Matrix Market file is missing its dimension line")

    dimension_lineno, dimension_line = data[0]
    dimensions = dimension_line.split()
    if len(dimensions) != 3:
        raise ValueError(f"line {dimension_lineno}: expected 'rows columns entries'")
    try:
        row_count, column_count, declared_entries = map(int, dimensions)
    except ValueError as exc:
        raise ValueError(f"line {dimension_lineno}: dimensions must be integers") from exc
    if row_count < 1 or column_count < 1 or declared_entries < 0:
        raise ValueError(f"line {dimension_lineno}: dimensions cannot be negative or empty")
    if row_count != column_count:
        raise ValueError("network adjacency matrix must be square")

    entry_lines = data[1:]
    if len(entry_lines) != declared_entries:
        raise ValueError(
            f"Matrix Market header declares {declared_entries} entries, "
            f"but {len(entry_lines)} were found"
        )

    edges: list[Edge] = []
    for lineno, line in entry_lines:
        parts = line.split()
        expected = 2 if field == "pattern" else 3
        if len(parts) != expected:
            raise ValueError(f"line {lineno}: expected {expected} values, got {len(parts)}")
        try:
            source_index = int(parts[0])
            target_index = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"line {lineno}: node indices must be integers") from exc
        if not (1 <= source_index <= row_count and 1 <= target_index <= column_count):
            raise ValueError(f"line {lineno}: node index is outside the declared matrix")

        weight = None if field == "pattern" else _number(parts[2], f"line {lineno}")
        weight = _validate_weight(weight, f"line {lineno}", ignore_weights)
        source, target = str(source_index), str(target_index)
        edges.append(Edge(source, target, weight))
        if (symmetry == "symmetric" or undirected) and source != target:
            edges.append(Edge(target, source, weight))

    nodes = tuple(str(index) for index in range(1, row_count + 1))
    return Network(nodes, _deduplicate_edges(edges))

# ------------------------------------------------------------------------------------

def _node_sort_key(node: str) -> tuple[int, int | str, str]:
    try:
        return (0, int(node), node)
    except ValueError:
        return (1, node.casefold(), node)

def _parse_edge_list(numbered_lines: Sequence[tuple[int, str]], undirected: bool, ignore_weights: bool) -> Network:
    nodes: set[str] = set()
    edges: list[Edge] = []

    for lineno, line in numbered_lines:
        if line.startswith(("#", "%")):
            continue
        parts = line.split()
        if len(parts) not in {2, 3}:
            raise ValueError(f"line {lineno}: expected 'u v [weight]'")
        source, target = parts[0], parts[1]
        weight = _number(parts[2], f"line {lineno}") if len(parts) == 3 else None
        weight = _validate_weight(weight, f"line {lineno}", ignore_weights)
        nodes.update((source, target))
        edges.append(Edge(source, target, weight))
        if undirected and source != target:
            edges.append(Edge(target, source, weight))

    if not nodes:
        raise ValueError("network file contains no nodes")
    return Network(tuple(sorted(nodes, key=_node_sort_key)), _deduplicate_edges(edges))

# ------------------------------------------------------------------------------------

def parse_network(lines: Iterable[str], *, undirected: bool = False, ignore_weights: bool = False) -> Network:
    """Parse formal Matrix Market input or a plain ``u v [weight]`` edge list."""

    numbered_lines = [
        (lineno, line.strip())
        for lineno, line in enumerate(lines, start=1)
        if line.strip()
    ]
    if not numbered_lines:
        raise ValueError("network file is empty")
    if numbered_lines[0][1].lower().startswith("%%matrixmarket"):
        return _parse_matrix_market(numbered_lines, undirected, ignore_weights)
    return _parse_edge_list(numbered_lines, undirected, ignore_weights)


def parse_assignment(value: str) -> tuple[str, str]:
    """Parse a CLI endpoint assignment written as ``NODE=FILE``."""

    node, separator, path = value.partition("=")
    if not separator or not node.strip() or not path.strip():
        raise ValueError("endpoint assignment must use NODE=FILE")
    return node.strip(), path.strip()


def _assignment_map(values: Sequence[str], mapping: dict[str, str], endpoint_name: str) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for value in values:
        node, path = parse_assignment(value)
        if node not in mapping:
            raise ValueError(f"{endpoint_name} node {node!r} is not in the network")
        if node in assignments:
            raise ValueError(f"{endpoint_name} node {node!r} was specified more than once")
        assignments[node] = path
    return assignments

# ------------------------------------------------------------------------------------

def _format_weight(weight: float) -> str:
    return f"{weight:.12g}"


def _format_edges(edges: Sequence[tuple[str, float | None]]) -> str:
    values = [
        qid if weight is None else f"{qid}:{_format_weight(weight)}"
        for qid, weight in edges
    ]
    return f"[{','.join(values)}]"


def build_config_rows(network: Network, options: ConfigOptions | None = None) -> tuple[list[list[str]], dict[str, str]]:
    """Return simulator config rows and the original-node to queue-ID mapping."""

    options = options if options is not None else ConfigOptions()
    if options.queue_size < 0:
        raise ValueError("queue size must be at least 0")
    if options.servers < 1:
        raise ValueError("number of servers must be at least 1")
    if options.rate < 1:
        raise ValueError("server function rate must be at least 1")
    if not options.function.strip():
        raise ValueError("server function cannot be empty")

    mapping = {node: f"q{index}" for index, node in enumerate(network.nodes)}
    incoming: dict[str, list[str]] = {node: [] for node in network.nodes}
    outgoing: dict[str, list[tuple[str, float | None]]] = {
        node: [] for node in network.nodes
    }
    for edge in network.edges:
        if edge.source not in mapping or edge.target not in mapping:
            raise ValueError(f"edge {edge.source}->{edge.target} references an unknown node")
        outgoing[edge.source].append((edge.target, edge.weight))
        incoming[edge.target].append(edge.source)

    order = {node: index for index, node in enumerate(network.nodes)}
    for node in network.nodes:
        incoming[node].sort(key=order.__getitem__)
        outgoing[node].sort(key=lambda item: order[item[0]])

    explicit_sources = _assignment_map(options.sources, mapping, "source")
    explicit_sinks = _assignment_map(options.sinks, mapping, "sink")
    sources: dict[str, str] = {}
    sinks: dict[str, str] = {}
    if options.auto_endpoints:
        for node in network.nodes:
            queue_index = order[node]
            if not incoming[node]:
                sources[node] = f"in{queue_index}.wl"
            if not outgoing[node]:
                sinks[node] = f"out{queue_index}.wl"
    sources.update(explicit_sources)
    sinks.update(explicit_sinks)

    rows: list[list[str]] = []
    for node in network.nodes:
        edges_in = _format_edges([(mapping[source], None) for source in incoming[node]])
        edges_out = _format_edges(
            [(mapping[target], weight) for target, weight in outgoing[node]]
        )
        rows.append(
            [
                mapping[node],
                str(options.queue_size),
                str(options.servers),
                options.function,
                str(options.rate),
                sources.get(node, ""),
                sinks.get(node, ""),
                edges_in,
                edges_out,
            ]
        )
    return rows, mapping

# ------------------------------------------------------------------------------------

def write_config(rows: Iterable[Sequence[str]], output: TextIO) -> None:
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert a Matrix Market graph or edge list into qconf.csv.")
    parser.add_argument("--network", required=True, help="Input .mtx or edge-list file")
    parser.add_argument("--out", default="qconf.csv", help="Output CSV (default: qconf.csv)")
    parser.add_argument("--queue-size", type=nonnegative_int, default=8)
    parser.add_argument("--servers", type=positive_int, default=1)
    parser.add_argument("--function", default="Sub-10", help="Server function (default: Sub-10)")
    parser.add_argument("--rate", type=positive_int, default=10)
    parser.add_argument("--undirected", action="store_true", help="Add the reverse of every edge")
    parser.add_argument("--ignore-weights", action="store_true", help="Emit equal-weight edges")
    parser.add_argument("--source", action="append", default=[], metavar="NODE=FILE", help="Assign a source workload to an original node ID (repeatable)")
    parser.add_argument("--sink", action="append", default=[], metavar="NODE=FILE", help="Assign a sink workload to an original node ID (repeatable)")
    parser.add_argument("--no-auto-endpoints", action="store_true", help="Do not infer sources at zero-in-degree nodes or sinks at zero-out-degree nodes")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with open(args.network, encoding="utf-8") as network_file:
            network = parse_network(
                network_file,
                undirected=args.undirected,
                ignore_weights=args.ignore_weights,
            )
        options = ConfigOptions(
            queue_size=args.queue_size,
            servers=args.servers,
            function=args.function,
            rate=args.rate,
            sources=tuple(args.source),
            sinks=tuple(args.sink),
            auto_endpoints=not args.no_auto_endpoints,
        )
        rows, mapping = build_config_rows(network, options)
        with open(args.out, "w", encoding="utf-8", newline="") as output:
            write_config(rows, output)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"create-config-from-network: {exc}") from exc

    source_count = sum(bool(row[5]) for row in rows)
    sink_count = sum(bool(row[6]) for row in rows)
    if source_count == 0:
        print(
            "create-config-from-network: warning: no source workload is assigned; "
            "use --source NODE=FILE to inject jobs",
            file=sys.stderr,
        )
    if sink_count == 0:
        print(
            "create-config-from-network: warning: no sink is assigned; "
            "use --sink NODE=FILE to collect completed jobs",
            file=sys.stderr,
        )
    if args.verbose:
        print(
            f"create-config-from-network: nodes={len(network.nodes)} "
            f"edges={len(network.edges)} sources={source_count} sinks={sink_count} "
            f"output={args.out}",
            file=sys.stderr,
        )
        print(
            "create-config-from-network: mapping="
            + ", ".join(f"{node}->{qid}" for node, qid in mapping.items()),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

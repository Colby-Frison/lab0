"""Tests for create-config-from-network."""

from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "create-config-network"))

import create_config_from_network as ccn  # noqa: E402

SRC_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = SRC_ROOT / "examples" / "obj-e" / "network-dummy.mtx"


class ParseTests(unittest.TestCase):
    def test_matrix_market_keeps_declared_nodes_and_weights(self):
        network = ccn.parse_network(
            [
                "%%MatrixMarket matrix coordinate real general\n",
                "% comment\n",
                "4 4 2\n",
                "1 2 2.5\n",
                "2 4 1.0\n",
            ]
        )
        self.assertEqual(network.nodes, ("1", "2", "3", "4"))
        self.assertEqual(
            network.edges,
            (ccn.Edge("1", "2", 2.5), ccn.Edge("2", "4", 1.0)),
        )

    def test_symmetric_matrix_adds_reverse_edges(self):
        network = ccn.parse_network(
            [
                "%%MatrixMarket matrix coordinate pattern symmetric\n",
                "3 3 2\n",
                "1 2\n",
                "2 3\n",
            ]
        )
        self.assertEqual(
            set(network.edges),
            {
                ccn.Edge("1", "2"),
                ccn.Edge("2", "1"),
                ccn.Edge("2", "3"),
                ccn.Edge("3", "2"),
            },
        )

    def test_plain_edge_list_sorts_numeric_node_ids(self):
        network = ccn.parse_network(["10 2\n", "2 7\n"])
        self.assertEqual(network.nodes, ("2", "7", "10"))

    def test_nonpositive_weight_can_only_be_ignored(self):
        lines = ["1 2 -4\n"]
        with self.assertRaisesRegex(ValueError, "positive"):
            ccn.parse_network(lines)
        network = ccn.parse_network(lines, ignore_weights=True)
        self.assertEqual(network.edges, (ccn.Edge("1", "2"),))


class ConfigTests(unittest.TestCase):
    def test_rows_have_topology_weights_and_inferred_endpoints(self):
        network = ccn.parse_network(EXAMPLE.read_text().splitlines())
        rows, mapping = ccn.build_config_rows(network)

        self.assertEqual(
            mapping,
            {"1": "q0", "2": "q1", "3": "q2", "4": "q3", "5": "q4"},
        )
        self.assertEqual(rows[0][5], "in0.wl")
        self.assertEqual(rows[0][7], "[]")
        self.assertEqual(rows[0][8], "[q1:2,q2:1]")
        self.assertEqual(rows[3][7], "[q1,q2]")
        self.assertEqual(rows[4][6], "out4.wl")
        self.assertEqual(rows[4][8], "[]")

    def test_explicit_endpoints_work_for_cycle(self):
        network = ccn.parse_network(["a b\n", "b a\n"])
        options = ccn.ConfigOptions(
            sources=("a=input.wl",),
            sinks=("b=output.wl",),
        )
        rows, _ = ccn.build_config_rows(network, options)
        self.assertEqual(rows[0][5], "input.wl")
        self.assertEqual(rows[1][6], "output.wl")

    def test_csv_writer_preserves_edge_lists_as_single_fields(self):
        network = ccn.parse_network(EXAMPLE.read_text().splitlines())
        rows, _ = ccn.build_config_rows(network)
        output = io.StringIO()
        ccn.write_config(rows, output)
        parsed = list(csv.reader(io.StringIO(output.getvalue())))
        self.assertEqual(parsed[0], ccn.HEADER)
        self.assertTrue(all(len(row) == 9 for row in parsed[1:]))
        self.assertEqual(parsed[1][8], "[q1:2,q2:1]")


class CliTests(unittest.TestCase):
    def test_cli_converts_repository_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "qconf.csv"
            rc = ccn.main(["--network", str(EXAMPLE), "--out", str(output)])
            self.assertEqual(rc, 0)
            rows = list(csv.reader(output.read_text().splitlines()))
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(len(row) == 9 for row in rows))


if __name__ == "__main__":
    unittest.main()

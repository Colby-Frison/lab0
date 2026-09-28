"""Tests for derive-sys-metrics (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "derive-sys-metrics"))

import derive_sys_metrics as dsm  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Worked example from src/design/obj-c/sysmetrics/README.md
DESIGN_EXAMPLE = """\
0 j0 IN q0 ARRIVE-VIA in0.wl
5 j1 IN q0 ARRIVE-VIA in0.wl
6 j2 IN q0 ARRIVE-VIA in0.wl
10 j0 IN q0 DEPART-VIA out0.wl
15 j1 IN q0 DEPART-VIA out0.wl
15 j2 IN q0 DEPART-VIA out0.wl
""".splitlines()


class ParseTests(unittest.TestCase):
    def test_parse_event_with_quoted_task(self):
        ev = dsm.parse_event('10 j0 IN q0 TASK-START 1 "W 10"')
        self.assertEqual(ev, dsm.Event(10, "j0", "q0", "TASK-START", '1 "W 10"'))

    def test_parse_event_rejects_garbage(self):
        self.assertIsNone(dsm.parse_event("hello world"))
        self.assertIsNone(dsm.parse_event("x j0 IN q0 ARRIVE-VIA in0.wl"))

    def test_iter_events_skips_blank_and_warns_on_bad(self):
        warnings: list[str] = []
        events = list(dsm.iter_events(["", "junk", "0 j0 IN q0 ARRIVE-VIA in0.wl"], warnings.append))
        self.assertEqual(len(events), 1)
        self.assertEqual(len(warnings), 1)


class DeriveTests(unittest.TestCase):
    def test_design_worked_example(self):
        rows = dsm.derive_system_metrics(DESIGN_EXAMPLE)
        self.assertEqual([r.time_step for r in rows], [10, 15])
        r10, r15 = rows
        self.assertEqual((r10.avg, r10.median, r10.p10, r10.p90, r10.throughput), (10, 10, 10, 10, 1))
        self.assertAlmostEqual(r15.avg, 9.5)
        self.assertAlmostEqual(r15.median, 9.5)
        self.assertAlmostEqual(r15.p10, 9.1)
        self.assertAlmostEqual(r15.p90, 9.9)
        self.assertEqual(r15.throughput, 2)

    def test_csv_output_matches_design_example(self):
        rows = dsm.derive_system_metrics(DESIGN_EXAMPLE)
        buf = io.StringIO()
        dsm.write_rows(rows, buf)
        self.assertEqual(
            buf.getvalue().splitlines(),
            [
                "time-step,Avg-response-time,median-response-time,10-response-time,90-response-time,throughput",
                "10,10.00,10.00,10.00,10.00,1",
                "15,9.50,9.50,9.10,9.90,2",
            ],
        )

    def test_internal_hops_are_ignored(self):
        """Multi-queue log: only source ARRIVE and sink DEPART count."""
        lines = (FIXTURES / "events-multi.log").read_text().splitlines()
        summary = dsm.Summary()
        rows = dsm.derive_system_metrics(lines, summary=summary)
        self.assertEqual(summary.queue_ids, {"q0", "q1"})
        self.assertEqual(summary.source_arrivals, 2)
        self.assertEqual(summary.sink_departures, 2)
        # j0: in at 0 (q0) out at 2 (q1 sink); j1: in at 1, out at 3 -> both 2 steps
        self.assertEqual([(r.time_step, r.throughput, r.avg) for r in rows], [(2, 1, 2.0), (3, 1, 2.0)])

    def test_single_queue_walkthrough(self):
        lines = (FIXTURES / "events-single.log").read_text().splitlines()
        rows = dsm.derive_system_metrics(lines)
        # j0 0->20, j1 10->30, j2 20->60
        self.assertEqual([(r.time_step, r.avg, r.throughput) for r in rows], [(20, 20.0, 1), (30, 20.0, 1), (60, 40.0, 1)])

    def test_window_groups_departures(self):
        rows = dsm.derive_system_metrics(DESIGN_EXAMPLE, window=10)
        self.assertEqual([(r.time_step, r.throughput) for r in rows], [(10, 3)])
        self.assertAlmostEqual(rows[0].avg, (10 + 10 + 9) / 3)

    def test_dense_fills_gaps_with_zero_throughput(self):
        rows = dsm.derive_system_metrics(DESIGN_EXAMPLE, window=5, dense=True)
        self.assertEqual([r.time_step for r in rows], [0, 5, 10, 15])
        self.assertEqual([r.throughput for r in rows], [0, 0, 1, 2])
        self.assertIsNone(rows[0].avg)
        buf = io.StringIO()
        dsm.write_rows(rows, buf)
        self.assertIn("0,,,,,0", buf.getvalue().splitlines())

    def test_dropped_job_is_reported_not_counted(self):
        lines = (FIXTURES / "events-queue-full.log").read_text().splitlines()
        summary = dsm.Summary()
        rows = dsm.derive_system_metrics(lines, summary=summary)
        self.assertEqual(summary.source_arrivals, 3)
        self.assertEqual(summary.sink_departures, 2)
        self.assertEqual(summary.still_in_system, 1)
        self.assertEqual(sum(r.throughput for r in rows), 2)

    def test_duplicate_job_ids_pair_fifo(self):
        lines = [
            "0 j0 IN q0 ARRIVE-VIA in0.wl",
            "1 j0 IN q0 ARRIVE-VIA in1.wl",
            "5 j0 IN q0 DEPART-VIA out0.wl",
            "9 j0 IN q0 DEPART-VIA out0.wl",
        ]
        rows = dsm.derive_system_metrics(lines)
        self.assertEqual([(r.time_step, r.avg) for r in rows], [(5, 5.0), (9, 8.0)])

    def test_window_must_be_positive(self):
        with self.assertRaises(ValueError):
            dsm.collect_response_times([], set(), window=0)


class CliTests(unittest.TestCase):
    def test_cli_writes_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sysmetrics.csv"
            rc = dsm.main(["--events", str(FIXTURES / "events-single.log"), "--out", str(out)])
            self.assertEqual(rc, 0)
            text = out.read_text().splitlines()
            self.assertEqual(text[0], ",".join(dsm.HEADER))
            self.assertEqual(len(text), 4)


if __name__ == "__main__":
    unittest.main()

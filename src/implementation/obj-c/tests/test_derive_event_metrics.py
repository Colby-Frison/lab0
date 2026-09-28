"""Tests for derive-event-metrics (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "derive-event-metrics"))

import derive_event_metrics as dem  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class DeriveTests(unittest.TestCase):
    def test_single_queue_matches_example_csv(self):
        """src/examples/obj-c/events/emetrics-ex.csv rows for j0..j2."""
        lines = (FIXTURES / "events-single.log").read_text().splitlines()
        rows = dem.derive_event_metrics(lines)
        got = [r.as_csv() for r in rows]
        self.assertEqual(
            got,
            [
                ["j0", "q0", "0", "0", "20", "0", "20"],
                ["j1", "q0", "10", "10", "10", "10", "20"],
                ["j2", "q0", "20", "10", "30", "10", "40"],
            ],
        )

    def test_multi_queue_one_row_per_visit(self):
        lines = (FIXTURES / "events-multi.log").read_text().splitlines()
        summary = dem.Summary()
        rows = dem.derive_event_metrics(lines, summary)
        self.assertEqual(summary.visits, 4)
        self.assertEqual(
            [(r.job, r.qsid, r.arrival, r.turnaround_time) for r in rows],
            [("j0", "q0", 0, 1), ("j0", "q1", 1, 1), ("j1", "q0", 1, 1), ("j1", "q1", 2, 1)],
        )

    def test_queue_full_visit_has_no_row(self):
        lines = (FIXTURES / "events-queue-full.log").read_text().splitlines()
        summary = dem.Summary()
        rows = dem.derive_event_metrics(lines, summary)
        self.assertEqual(summary.dropped, 1)
        self.assertEqual({r.job for r in rows}, {"j0", "j1"})
        # j1 waited 10 steps behind j0 in a single-server queue
        j1 = next(r for r in rows if r.job == "j1")
        self.assertEqual((j1.time_in_queue, j1.time_in_service, j1.response_time), (10, 10, 10))

    def test_response_time_equals_time_in_queue(self):
        row = dem.VisitRow("j9", "q3", arrival=4, entered=9, exited=21)
        self.assertEqual(row.response_time, 5)
        self.assertEqual(row.time_in_queue, 5)
        self.assertEqual(row.time_in_service, 12)
        self.assertEqual(row.turnaround_time, 17)

    def test_incomplete_visit_is_counted(self):
        lines = ["0 j0 IN q0 ARRIVE-VIA in0.wl", "0 j0 IN q0 ENTERS-SERVER 0"]
        summary = dem.Summary()
        rows = dem.derive_event_metrics(lines, summary)
        self.assertEqual(rows, [])
        self.assertEqual(summary.incomplete, 1)

    def test_depart_closes_visit_when_exit_missing(self):
        lines = [
            "0 j0 IN q0 ARRIVE-VIA in0.wl",
            "3 j0 IN q0 ENTERS-SERVER 0",
            "8 j0 IN q0 DEPART-VIA out0.wl",
        ]
        rows = dem.derive_event_metrics(lines)
        self.assertEqual(rows[0].as_csv(), ["j0", "q0", "0", "3", "5", "3", "8"])

    def test_csv_header(self):
        buf = io.StringIO()
        dem.write_rows([], buf)
        self.assertEqual(
            buf.getvalue().strip(),
            "Job-id,Queue-sys-id,arrival-time,time-in-queue,time-in-service,response-time,turnaround-time",
        )


class CliTests(unittest.TestCase):
    def test_cli_writes_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "emetrics.csv"
            rc = dem.main(["--events", str(FIXTURES / "events-multi.log"), "--out", str(out)])
            self.assertEqual(rc, 0)
            text = out.read_text().splitlines()
            self.assertEqual(len(text), 5)  # header + 4 visits


if __name__ == "__main__":
    unittest.main()

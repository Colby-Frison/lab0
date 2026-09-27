"""Tests for create-event-trace (run: python -m unittest discover -s tests -v)"""

from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "create-event-trace"))

import create_event_trace as cet  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParseTests(unittest.TestCase):
    def test_parse_event_with_quoted_task(self):
        event = cet.parse_event('7 j3 IN q2 TASK-START 1 "W 10"')
        self.assertEqual(
            event,
            cet.Event(
                time=7,
                job="j3",
                qsid="q2",
                kind="TASK-START",
                details='1 "W 10"',
            ),
        )

    def test_parse_event_rejects_garbage(self):
        self.assertIsNone(cet.parse_event("not an event"))
        self.assertIsNone(cet.parse_event("x j0 IN q0 ARRIVE-VIA in0.wl"))
        self.assertIsNone(cet.parse_event("0 j0 AT q0 ARRIVE-VIA in0.wl"))

    def test_iter_events_skips_blank_and_warns_on_bad_line(self):
        warnings: list[str] = []
        events = list(
            cet.iter_events(
                ["", "bad line", "0 j0 IN q0 ARRIVE-VIA in0.wl"],
                warnings.append,
            )
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].job, "j0")
        self.assertEqual(len(warnings), 1)
        self.assertIn("line 2", warnings[0])


class TraceTests(unittest.TestCase):
    def test_first_jobs_preserves_appearance_order_and_limit(self):
        events = [
            cet.Event(0, "j2", "q0", "ARRIVE-VIA"),
            cet.Event(1, "j2", "q0", "TASK-START"),
            cet.Event(2, "j0", "q0", "ARRIVE-VIA"),
            cet.Event(3, "j1", "q1", "ARRIVE-VIA"),
        ]
        self.assertEqual(cet.first_jobs(events), ["j2", "j0", "j1"])
        self.assertEqual(cet.first_jobs(events, limit=2), ["j2", "j0"])

    def test_plot_creates_png_and_honors_limit(self):
        lines = (FIXTURES / "events-multi.log").read_text().splitlines()
        events = list(cet.iter_events(lines))

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "etrace.png"
            jobs_plotted = cet.plot_event_trace(events, out, limit=1)

            self.assertEqual(jobs_plotted, 1)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 1000)
            self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_plot_rejects_empty_event_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "no valid events"):
                cet.plot_event_trace([], Path(tmp) / "etrace.png")

    def test_positive_int_rejects_zero(self):
        self.assertEqual(cet.positive_int("3"), 3)
        with self.assertRaises(argparse.ArgumentTypeError):
            cet.positive_int("0")


class CliTests(unittest.TestCase):
    def test_cli_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "etrace.png"
            rc = cet.main(
                [
                    "--events",
                    str(FIXTURES / "events-single.log"),
                    "--limit",
                    "2",
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertGreater(out.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()

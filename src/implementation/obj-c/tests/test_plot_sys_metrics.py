"""Tests for plot-sys-metrics (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plot-sys-metrics"))

import plot_sys_metrics as psm  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class PlotTests(unittest.TestCase):
    def test_plots_example_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "resplot.png"
            rc = psm.main(["--sysmetrics", str(FIXTURES / "sysmetrics-ex.csv"), "--out", str(out), "--title", "t"])
            self.assertEqual(rc, 0)
            self.assertGreater(out.stat().st_size, 1000)

    def test_plots_dense_csv_with_gaps(self):
        """Rows with empty percentiles (no departures) must not crash the plot."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "resplot.png"
            rc = psm.main(
                ["--sysmetrics", str(FIXTURES / "sysmetrics-dense.csv"), "--out", str(out), "--xlim", "0:20", "--no-band"]
            )
            self.assertEqual(rc, 0)
            self.assertGreater(out.stat().st_size, 1000)

    def test_missing_columns_fail_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text("time-step,throughput\n1,2\n")
            with self.assertRaises(SystemExit):
                psm.load_sysmetrics(str(bad))

    def test_parse_pair(self):
        self.assertEqual(psm.parse_pair("0:10"), (0.0, 10.0))


if __name__ == "__main__":
    unittest.main()

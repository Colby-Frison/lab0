"""Tests for plot-use (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plot-use"))

import plot_use as pu  # noqa: E402

QUSE = """\
time-step,queue-sys-id,Utilization(10),Saturation(10),Errors(10),Utilization(100),Saturation(100),Errors(100),Utilization(1000),Saturation(1000),Errors(1000)
0,0,0.0,0.0,0,0.0,0.0,0,0.0,0.0,0
1,0,0.5,1.0,0,0.5,1.0,0,0.5,1.0,0
0,1,1.0,0.0,0,1.0,0.0,0,1.0,0.0,0
1,1,1.0,2.0,1,1.0,2.0,1,1.0,2.0,1
"""


class PlotTests(unittest.TestCase):
    def test_writes_a_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "quse.csv"
            dest = Path(tmp) / "use.png"
            src.write_text(QUSE, encoding="utf-8")
            df = pu.load_quse(str(src))
            pu.plot_use(df, str(dest), title="test")
            self.assertGreater(dest.stat().st_size, 100)
            self.assertEqual(dest.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()

"""Checks for derived job-metric histograms and scatter plots."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plot-derive-event-metrics"))
import plot_derive_event_metrics as pem


class HistogramTests(unittest.TestCase):
    def test_bins_counts_and_display_options(self):
        data = pd.DataFrame({"arrival-time": [0, 1, 2, 3]})
        with patch.object(pem.plt.Figure, "savefig") as save:
            def inspect_plot(*args, **kwargs):
                ax = pem.plt.gcf().axes[0]
                self.assertEqual([bar.get_height() for bar in ax.patches], [2, 2])
                self.assertEqual(ax.get_title(), "Arrivals")
                self.assertEqual(ax.get_xlim(), (0, 1))
                self.assertEqual(ax.get_ylim(), (0, 5))
            save.side_effect = inspect_plot
            pem.plot_histogram(data, "arrival-time", 2, "unused.png", "Arrivals", (0, 1), (0, 5))
            save.assert_called_once()
        self.assertEqual(pem.plt.get_fignums(), [])

    def test_cli_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "metrics.csv", Path(tmp) / "hist.png"
            source.write_text("arrival-time\n0\n10\n20\n")
            self.assertEqual(pem.main([str(source), str(output), "--hist", "arrival-time"]), 0)
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_invalid_columns_and_values(self):
        for data in ({"other": [1]}, {"x": []}, {"x": ["bad"]}, {"x": [float("nan")]}, {"x": [float("inf")]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                pem.plot_histogram(pd.DataFrame(data), "x", 10, "unused.png")


class ScatterTests(unittest.TestCase):
    def test_preserves_pairs_and_display_options(self):
        data = pd.DataFrame({"arrival-time": [20, 0, 10], "response-time": [3, 9, 1]})
        with patch.object(pem.plt.Figure, "savefig") as save:
            def inspect_plot(*args, **kwargs):
                ax = pem.plt.gcf().axes[0]
                self.assertEqual(ax.collections[0].get_offsets().tolist(), [[20, 3], [0, 9], [10, 1]])
                self.assertEqual(ax.get_xlabel(), "arrival-time")
                self.assertEqual(ax.get_ylabel(), "response-time")
                self.assertEqual(ax.get_title(), "Responses")
                self.assertEqual(ax.get_xlim(), (0, 30))
                self.assertEqual(ax.get_ylim(), (0, 10))
            save.side_effect = inspect_plot
            pem.plot_scatter(data, "arrival-time", "response-time", "unused.png", "Responses", (0, 30), (0, 10))
            save.assert_called_once()
        self.assertEqual(pem.plt.get_fignums(), [])

    def test_cli_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "metrics.csv", Path(tmp) / "scatter.png"
            source.write_text("arrival-time,response-time\n0,10\n10,20\n20,5\n")
            self.assertEqual(pem.main([str(source), str(output), "--scat", "arrival-time, response-time"]), 0)
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_rejects_invalid_data_on_either_axis(self):
        for axis in ("x", "y"):
            for invalid in (None, "bad", float("inf")):
                data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
                data[axis] = [1, invalid]
                with self.subTest(axis=axis, invalid=invalid), self.assertRaises(ValueError):
                    pem.plot_scatter(data, "x", "y", "unused.png")
            with self.subTest(missing=axis), self.assertRaises(ValueError):
                pem.plot_scatter(pd.DataFrame({axis: [1]}), "x", "y", "unused.png")
        with self.assertRaises(ValueError):
            pem.plot_scatter(pd.DataFrame({"x": [], "y": []}), "x", "y", "unused.png")

    def test_closes_figure_on_save_failure(self):
        with patch.object(pem.plt.Figure, "savefig", side_effect=OSError("Cannot save")):
            with self.assertRaises(OSError):
                pem.plot_scatter(pd.DataFrame({"x": [1], "y": [2]}), "x", "y", "unused.png")
        self.assertEqual(pem.plt.get_fignums(), [])


if __name__ == "__main__":
    unittest.main()

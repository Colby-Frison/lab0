"""Tests for compute-use (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "compute-use"))

import compute_use as cu  # noqa: E402


def qmet(text: str) -> "cu.pd.DataFrame":
    return cu.read_qmet(io.StringIO(textwrap.dedent(text).strip() + "\n"))


def write_config(directory: Path, body: str) -> Path:
    path = directory / "qconf.csv"
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return path


class ServerCountTests(unittest.TestCase):
    def test_prefixed_id_and_commas_inside_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_config(
                Path(tmp),
                """
                Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
                q0,8,2,Sub-10,10,in.wl,,[],[q1,q2]
                """,
            )
            self.assertEqual(cu.load_server_counts(str(path)), {"0": 2})


class ComputeTests(unittest.TestCase):
    HEADER = (
        "time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors"
    )

    def test_short_history_makes_every_window_match(self):
        frame = qmet(
            f"""
            {self.HEADER}
            0,0,0,0,0
            1,0,2,1,0
            2,0,1,1,1
            """
        )
        out = cu.compute_use(frame, {"0": 1})
        last = out.iloc[-1]
        self.assertEqual(last["time-step"], 2)
        for size in (10, 100, 1000):
            self.assertAlmostEqual(last[f"Utilization({size})"], 2 / 3, places=5)
            self.assertAlmostEqual(last[f"Saturation({size})"], 1.0, places=5)
            self.assertEqual(last[f"Errors({size})"], 1)

    def test_queues_do_not_share_a_window(self):
        frame = qmet(
            f"""
            {self.HEADER}
            0,0,4,1,0
            0,1,0,0,3
            """
        )
        out = cu.compute_use(frame, {"0": 1, "1": 1})
        by_q = {row["queue-sys-id"]: row for _, row in out.iterrows()}
        self.assertAlmostEqual(by_q["0"]["Saturation(10)"], 4.0)
        self.assertEqual(by_q["0"]["Errors(10)"], 0)
        self.assertAlmostEqual(by_q["1"]["Saturation(10)"], 0.0)
        self.assertEqual(by_q["1"]["Errors(10)"], 3)

    def test_window_10_drops_the_oldest_step(self):
        lines = [self.HEADER, "0,0,0,0,0"]
        lines.extend(f"{step},0,0,1,0" for step in range(1, 11))
        out = cu.compute_use(qmet("\n".join(lines) + "\n"), {"0": 1})
        last = out.iloc[-1]
        self.assertAlmostEqual(last["Utilization(10)"], 1.0, places=5)
        self.assertAlmostEqual(last["Utilization(100)"], 10 / 11, places=5)

    def test_config_prefix_matches_numeric_qmet(self):
        frame = qmet(
            f"""
            {self.HEADER}
            0,0,0,1,0
            """
        )
        out = cu.compute_use(frame, {"0": 2})
        self.assertAlmostEqual(out.iloc[0]["Utilization(10)"], 0.5, places=5)

    def test_cli_joins_q0_config_to_numeric_qmet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qmet_path = root / "qmet.csv"
            qmet_path.write_text(
                textwrap.dedent(
                    f"""
                    {self.HEADER}
                    0,0,0,1,0
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            config = write_config(
                root,
                """
                Sys ID,Queue Max Size,Num. Servers,Server Function,Server Function Rate,Source,Sink,Edges in,Edges out
                q0,8,2,Sub-10,10,in.wl,,[],[q1,q2]
                """,
            )
            out = root / "quse.csv"
            code = cu.main(["--qmet", str(qmet_path), "--config", str(config), "--out", str(out)])
            self.assertEqual(code, 0)
            row = next(iter(cu.pd.read_csv(out).itertuples(index=False)))
            self.assertEqual(row[1], 0)
            self.assertAlmostEqual(row[2], 0.5, places=5)

    def test_missing_config_row_is_an_error(self):
        frame = qmet(
            f"""
            {self.HEADER}
            0,2,0,1,0
            """
        )
        with self.assertRaises(ValueError):
            cu.compute_use(frame, {"0": 1})


if __name__ == "__main__":
    unittest.main()

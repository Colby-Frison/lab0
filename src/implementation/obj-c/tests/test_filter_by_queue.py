"""Tests for filter-by-queue (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "filter-by-queue"))

import filter_by_queue as fbq  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
QMET_MULTI = FIXTURES / "qmet-multi.csv"
HEADER = "time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors"

# Worked example from src/design/obj-c/filters/README.md
DESIGN_EXAMPLE = """\
time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors
0,0,1,1,0
0,1,0,0,0
1,0,2,1,0
"""


def filter_text(text: str, qids: list[str]) -> str:
    df = fbq.filter_by_queue(fbq.read_qmet(io.StringIO(text)), qids)
    buf = io.StringIO()
    fbq.write_qmet(df, buf)
    return buf.getvalue()


class ParseQidTests(unittest.TestCase):
    def test_single_id(self):
        self.assertEqual(fbq.parse_qids("0"), ["0"])

    def test_list_with_spaces(self):
        self.assertEqual(fbq.parse_qids("0, 1 ,2"), ["0", "1", "2"])

    def test_prefixed_and_padded_ids_are_normalized(self):
        self.assertEqual(fbq.parse_qids("q0,Q1,007"), ["0", "1", "7"])

    def test_duplicates_removed_order_kept(self):
        self.assertEqual(fbq.parse_qids("2,q0,0,2"), ["2", "0"])

    def test_invalid_specs_raise(self):
        for spec in ("", ",", "abc", "0,,1"):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                fbq.parse_qids(spec)


class FilterTests(unittest.TestCase):
    def test_design_worked_example(self):
        self.assertEqual(
            filter_text(DESIGN_EXAMPLE, ["0"]).splitlines(),
            [HEADER, "0,0,1,1,0", "1,0,2,1,0"],
        )

    def test_single_queue_keeps_its_rows_in_order(self):
        lines = filter_text(QMET_MULTI.read_text(), ["1"]).splitlines()
        self.assertEqual(lines, [HEADER, "0,1,0,0,0", "1,1,1,1,0", "2,1,0,1,0", "3,1,0,0,0"])

    def test_multiple_queues_interleave_in_time_order(self):
        lines = filter_text(QMET_MULTI.read_text(), ["2", "0"]).splitlines()
        self.assertEqual(
            [line.split(",")[:2] for line in lines[1:]],
            [["0", "0"], ["0", "2"], ["1", "0"], ["1", "2"], ["2", "0"], ["2", "2"], ["3", "0"], ["3", "2"]],
        )

    def test_unknown_queue_gives_header_only(self):
        self.assertEqual(filter_text(QMET_MULTI.read_text(), ["9"]), HEADER + "\n")

    def test_round_trip_is_byte_identical(self):
        text = QMET_MULTI.read_text()
        self.assertEqual(filter_text(text, ["0", "1", "2"]), text)

    def test_cells_are_not_reformatted(self):
        text = f"{HEADER},note\n0,0,01,1.50,0,\n"
        self.assertEqual(filter_text(text, ["0"]), text)

    def test_file_ids_are_compared_exactly(self):
        text = f"{HEADER}\n0,q0,1,1,0\n"
        self.assertEqual(filter_text(text, ["0"]), HEADER + "\n")

    def test_missing_column_raises(self):
        with self.assertRaises(ValueError):
            fbq.read_qmet(io.StringIO("time-step,queue,num\n0,0,1\n"))


class CliTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fbq.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_cli_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "q0_metrics.csv"
            rc, stdout, _ = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "0", "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertEqual(stdout, "")
            self.assertEqual(
                out.read_text().splitlines(),
                [HEADER, "0,0,1,1,0", "1,0,2,1,0", "2,0,3,1,1", "3,0,2,1,0"],
            )

    def test_cli_defaults_to_stdout(self):
        rc, stdout, _ = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "2"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(stdout.splitlines()), 5)

    def test_cli_accepts_list(self):
        _, stdout, _ = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "0,2"])
        self.assertEqual(len(stdout.splitlines()), 1 + 8)

    def test_cli_prefixed_id_equals_numeric(self):
        _, a, _ = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "q0"])
        _, b, _ = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "0"])
        self.assertEqual(a, b)

    def test_cli_warns_on_missing_id(self):
        rc, stdout, stderr = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "0,9"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(stdout.splitlines()), 5)
        self.assertIn("9 not found", stderr)
        self.assertIn("available: 0,1,2", stderr)

    def test_cli_verbose_reports_counts(self):
        _, _, stderr = self.run_main(["--qmet", str(QMET_MULTI), "--qid", "0", "-v"])
        self.assertIn("queues_in_file=['0', '1', '2']", stderr)
        self.assertIn("rows_in=12 rows_out=4", stderr)

    def test_cli_missing_file_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(["--qmet", str(FIXTURES / "nope.csv"), "--qid", "0"])
        self.assertIn("cannot read", str(ctx.exception.code))

    def test_cli_bad_qid_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(["--qmet", str(QMET_MULTI), "--qid", "abc"])
        self.assertIn("--qid", str(ctx.exception.code))

    def test_cli_requires_qid(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(["--qmet", str(QMET_MULTI)])
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()

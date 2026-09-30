"""Tests for filter-by-job (run: python -m unittest discover -s tests -v)."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "filter-by-job"))

import filter_by_job as fbj  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
EVENTS_SINGLE = FIXTURES / "events-single.log"
EVENTS_MULTI = FIXTURES / "events-multi.log"


def filter_text(text: str, job_ids: list[str]) -> str:
    return "".join(fbj.filter_by_job(io.StringIO(text), job_ids))


class ParseJobIdsTests(unittest.TestCase):
    def test_bare_number_gets_prefix(self):
        self.assertEqual(fbj.parse_job_ids("0"), ["j0"])

    def test_list_mixed_forms_deduplicated(self):
        self.assertEqual(fbj.parse_job_ids("0, j1,1"), ["j0", "j1"])

    def test_padded_number_normalized(self):
        self.assertEqual(fbj.parse_job_ids("007"), ["j7"])

    def test_prefixed_id_kept(self):
        self.assertEqual(fbj.parse_job_ids("j12"), ["j12"])

    def test_empty_tokens_raise(self):
        for spec in ("", "0,,1"):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                fbj.parse_job_ids(spec)


class FilterTests(unittest.TestCase):
    def test_single_job_lines_unchanged_in_order(self):
        text = EVENTS_SINGLE.read_text()
        expected = "".join(line for line in text.splitlines(keepends=True) if line.split()[1] == "j1")
        self.assertEqual(filter_text(text, ["j1"]), expected)
        self.assertEqual(len(expected.splitlines()), 6)

    def test_multiple_jobs_keep_interleaving(self):
        text = EVENTS_MULTI.read_text()
        self.assertEqual(filter_text(text, ["j0", "j1"]), text)

    def test_only_second_token_is_compared(self):
        text = "5 j1 IN q0 TASK-START 0 j0\n6 j0 IN q0 ARRIVE-VIA in0.wl\n"
        self.assertEqual(filter_text(text, ["j0"]), "6 j0 IN q0 ARRIVE-VIA in0.wl\n")

    def test_no_substring_match(self):
        text = "0 j10 IN q0 ARRIVE-VIA in0.wl\n1 j1 IN q0 ARRIVE-VIA in0.wl\n"
        self.assertEqual(filter_text(text, ["j1"]), "1 j1 IN q0 ARRIVE-VIA in0.wl\n")

    def test_unknown_job_gives_empty_output(self):
        self.assertEqual(filter_text(EVENTS_SINGLE.read_text(), ["j9"]), "")

    def test_blank_and_short_lines_skipped(self):
        text = "\n   \nj0\n0 j0 IN q0 ARRIVE-VIA in0.wl\n"
        self.assertEqual(filter_text(text, ["j0"]), "0 j0 IN q0 ARRIVE-VIA in0.wl\n")


class CliTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = fbj.main(argv)
        return rc, out.getvalue()

    def test_cli_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "j2_events.log"
            rc, stdout = self.run_main(["--events", str(EVENTS_SINGLE), "--jobs", "2", "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertEqual(stdout, "")
            lines = out.read_text().splitlines()
            self.assertEqual(len(lines), 10)
            self.assertTrue(all(line.split()[1] == "j2" for line in lines))

    def test_cli_defaults_to_stdout(self):
        rc, stdout = self.run_main(["--events", str(EVENTS_SINGLE), "--jobs", "j0"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(stdout.splitlines()), 8)

    def test_cli_equals_and_space_forms_match(self):
        _, a = self.run_main(["--events", str(EVENTS_SINGLE), "--jobs=0"])
        _, b = self.run_main(["--events", str(EVENTS_SINGLE), "--jobs", "0"])
        _, c = self.run_main(["--events", str(EVENTS_SINGLE), "--jobs", "j0"])
        self.assertEqual(a, b)
        self.assertEqual(a, c)

    def test_cli_missing_file_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(["--events", str(FIXTURES / "nope.log"), "--jobs", "0"])
        self.assertIn("filter-by-job", str(ctx.exception.code))

    def test_cli_requires_jobs(self):
        with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stderr(io.StringIO()):
            self.run_main(["--events", str(EVENTS_SINGLE)])
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()

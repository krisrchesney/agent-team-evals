"""Hidden tests for t24-cli-export. Every rule is shown by the starting code; see AUDIT.md."""
import csv
import io
import json
import os
import tempfile
import unittest

from tasklog import main
from tasklog.clock import FixedClock

HEADER = ["id", "title", "project", "status", "priority", "tags", "due", "created"]
ROWS = [
    ["1", "Buy milk", "home", "open", "2", "errand;dairy", "2026-03-05", "2026-03-02T09:00:00Z"],
    ["2", 'Write "report", draft', "work", "open", "1", "q1", "2026-03-20", "2026-03-02T09:01:00Z"],
    ["3", "Plan trip to Zürich 日本", "home", "open", "3", "", "", "2026-03-02T09:02:00Z"],
    ["4", "Pay rent", "home", "done", "1", "money", "2026-03-01", "2026-03-02T09:03:00Z"],
]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = os.path.join(self.tmp.name, "tasks.json")
        self.out = os.path.join(self.tmp.name, "out.csv")
        self.clock = FixedClock()
        self.cli("add", "Buy milk", "--project", "home", "--due", "2026-03-05", "--tag", "errand", "--tag", "dairy")
        self.clock.advance(minutes=1)
        self.cli("add", 'Write "report", draft', "--project", "work", "--priority", "1", "--tag", "q1",
                 "--due", "2026-03-20")
        self.clock.advance(minutes=1)
        self.cli("add", "Plan trip to Zürich 日本", "--project", "home", "--priority", "3")
        self.clock.advance(minutes=1)
        self.cli("add", "Pay rent", "--project", "home", "--priority", "1", "--tag", "money", "--due", "2026-03-01")
        self.cli("done", "4")

    def cli(self, *argv, store=None):
        out, err = io.StringIO(), io.StringIO()
        code = main(["--store", store or self.store, *argv], stdout=out, stderr=err, clock=self.clock)
        return code, out.getvalue(), err.getvalue()

    def export(self, *argv, **kw):
        return self.cli("export", *argv, **kw)

    def read_csv(self, path=None):
        with open(path or self.out, encoding="utf-8", newline="") as fh:
            return list(csv.reader(fh))

    def read_json(self, path=None):
        with open(path or self.out, encoding="utf-8") as fh:
            return json.load(fh)

    def ids(self, rows):
        return [r[0] for r in rows[1:]]

    def listing(self):
        return json.loads(self.cli("list", "--json", "--limit", "100")[1])["items"]


class TestFiles(Base):
    def test_csv_is_the_default_and_matches_the_task_rows(self):
        code, out, err = self.export("--output", self.out)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self.read_csv(), [HEADER] + ROWS)

    def test_csv_survives_commas_quotes_newlines_and_unicode(self):
        self.cli("add", 'Say "hi", then\nleave ☃')
        self.export("--output", self.out)
        self.assertEqual(self.read_csv()[-1][1], 'Say "hi", then\nleave ☃')
        raw = open(self.out, "rb").read().decode("utf-8")
        self.assertIn("Zürich 日本", raw)

    def test_json_file_is_the_list_json_items(self):
        self.export("--output", self.out, "--format", "json")
        self.assertEqual(self.read_json(), self.listing())
        self.assertEqual(self.read_json()[0]["tags"], ["errand", "dairy"])
        self.assertIsNone(self.read_json()[2]["due"])

    def test_json_file_is_utf8_whatever_the_locale(self):
        self.export("--output", self.out, "--format", "json")
        self.assertEqual(self.read_json()[2]["title"], "Plan trip to Zürich 日本")

    def test_tasks_are_in_id_order(self):
        self.export("--output", self.out)
        self.assertEqual(self.ids(self.read_csv()), ["1", "2", "3", "4"])


class TestFilters(Base):
    def test_filters_work_like_list(self):
        cases = [
            (["--project", "home"], ["1", "3", "4"]),
            (["--status", "open"], ["1", "2", "3"]),
            (["--status", "done"], ["4"]),
            (["--tag", "q1"], ["2"]),
            (["--due-before", "2026-03-10"], ["1", "4"]),
            (["--project", "home", "--status", "open", "--due-before", "2026-03-10"], ["1"]),
        ]
        for argv, expected in cases:
            with self.subTest(argv):
                if os.path.exists(self.out):
                    os.unlink(self.out)
                self.assertEqual(self.export("--output", self.out, *argv)[0], 0)
                self.assertEqual(self.ids(self.read_csv()), expected)
                listed = [str(i["id"]) for i in json.loads(self.cli("list", "--json", *argv)[1])["items"]]
                self.assertEqual(listed, expected)

    def test_json_filters_and_count(self):
        code, out, _ = self.export("--output", self.out, "--format", "json", "--project", "home", "--json")
        self.assertEqual(json.loads(out)["count"], 3)
        self.assertEqual([t["id"] for t in self.read_json()], [1, 3, 4])

    def test_unknown_project_is_not_found(self):
        code, out, err = self.export("--output", self.out, "--project", "nosuch")
        self.assertEqual((code, out), (3, ""))
        self.assertTrue(err.startswith("tasklog: error: "), err)
        self.assertIn("nosuch", err)
        self.assertFalse(os.path.exists(self.out))

    def test_bad_date_is_a_usage_error(self):
        code, out, err = self.export("--output", self.out, "--due-before", "next week")
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("tasklog: error: "), err)
        self.assertFalse(os.path.exists(self.out))

    def test_bad_format_and_missing_output_are_usage_errors(self):
        self.assertEqual(self.export("--output", self.out, "--format", "xml")[0], 2)
        self.assertEqual(self.export()[0], 2)
        self.assertEqual(os.listdir(self.tmp.name), ["tasks.json"])


class TestOutput(Base):
    def test_text_summary(self):
        code, out, err = self.export("--output", self.out)
        self.assertEqual(err, "")
        self.assertIn("4", out)
        self.assertIn(self.out, out)
        self.assertEqual(len(out.strip().splitlines()), 1)

    def test_json_summary(self):
        code, out, err = self.export("--output", self.out, "--json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out),
                         {"command": "export", "count": 4, "format": "csv", "output": self.out})

    def test_json_summary_names_the_format_and_path_as_given(self):
        given = os.path.join(self.tmp.name, "sub", "..", "out.json")
        os.mkdir(os.path.join(self.tmp.name, "sub"))
        code, out, _ = self.export("--output", given, "--format", "json", "--json")
        self.assertEqual(json.loads(out),
                         {"command": "export", "count": 4, "format": "json", "output": given})

    def test_quiet_silences_the_text_but_not_json(self):
        code, out, err = self.cli("-q", "export", "--output", self.out)
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertEqual(len(self.read_csv()), 5)
        os.unlink(self.out)
        code, out, _ = self.cli("-q", "export", "--output", self.out, "--json")
        self.assertEqual(json.loads(out)["count"], 4)

    def test_the_store_is_not_changed(self):
        before = open(self.store, "rb").read()
        self.export("--output", self.out)
        self.export("--output", self.out, "--force", "--format", "json")
        self.assertEqual(open(self.store, "rb").read(), before)

    def test_a_missing_store_is_empty_and_stays_missing(self):
        missing = os.path.join(self.tmp.name, "nothing.json")
        code, out, err = self.export("--output", self.out, store=missing)
        self.assertEqual(code, 0)
        self.assertEqual(self.read_csv(), [HEADER])
        self.assertFalse(os.path.exists(missing))
        self.assertTrue(err.startswith("tasklog: warning: "), err)


class TestEmpty(Base):
    def test_no_matching_tasks_still_writes_the_file_and_warns(self):
        code, out, err = self.export("--output", self.out, "--tag", "nosuchtag", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["count"], 0)
        self.assertEqual(self.read_csv(), [HEADER])
        self.assertTrue(err.startswith("tasklog: warning: "), err)
        self.assertEqual(len(err.strip().splitlines()), 1)

    def test_empty_json_file_is_an_empty_list(self):
        self.export("--output", self.out, "--format", "json", "--tag", "nosuchtag")
        self.assertEqual(self.read_json(), [])

    def test_warnings_are_not_silenced_by_quiet(self):
        code, out, err = self.cli("-q", "export", "--output", self.out, "--tag", "nosuchtag")
        self.assertEqual((code, out), (0, ""))
        self.assertTrue(err.startswith("tasklog: warning: "), err)


class TestFailures(Base):
    def test_existing_output_is_a_conflict(self):
        with open(self.out, "w", encoding="utf-8") as fh:
            fh.write("precious")
        code, out, err = self.export("--output", self.out)
        self.assertEqual((code, out), (5, ""))
        self.assertTrue(err.startswith("tasklog: error: "), err)
        self.assertIn(self.out, err)
        self.assertEqual(open(self.out, encoding="utf-8").read(), "precious")

    def test_force_replaces_the_file(self):
        with open(self.out, "w", encoding="utf-8") as fh:
            fh.write("old")
        self.assertEqual(self.export("--output", self.out, "--force")[0], 0)
        self.assertEqual(len(self.read_csv()), 5)

    def test_unwritable_output_is_an_io_failure(self):
        target = os.path.join(self.tmp.name, "no-such-dir", "out.csv")
        code, out, err = self.export("--output", target)
        self.assertEqual((code, out), (4, ""))
        self.assertTrue(err.startswith("tasklog: error: "), err)
        self.assertIn(target, err)
        self.assertEqual(os.listdir(self.tmp.name), ["tasks.json"])

    def test_no_temporary_files_are_left_behind(self):
        self.export("--output", self.out)
        self.export("--output", self.out)
        self.export("--output", self.out, "--force")
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["out.csv", "tasks.json"])

    def test_errors_in_json_mode(self):
        cases = [
            (["--output", os.path.join(self.tmp.name, "gone", "o.csv")], 4),
            (["--output", self.store], 5),
            (["--output", self.out, "--project", "nosuch"], 3),
            (["--output", self.out, "--due-before", "soon"], 2),
        ]
        for argv, code in cases:
            with self.subTest(argv):
                got, out, err = self.export(*argv, "--json")
                self.assertEqual((got, out), (code, ""))
                body = json.loads(err)
                self.assertEqual(body["command"], "export")
                self.assertEqual(body["error"]["code"], code)
                self.assertIsInstance(body["error"]["message"], str)

    def test_a_corrupt_store_is_an_io_failure(self):
        with open(self.store, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        code, out, err = self.export("--output", self.out)
        self.assertEqual((code, out), (4, ""))
        self.assertTrue(err.startswith("tasklog: error: "), err)
        self.assertFalse(os.path.exists(self.out))


class TestRegression(Base):
    def test_other_commands_unchanged(self):
        self.assertEqual(self.cli("show", "1", "--json")[0], 0)
        self.assertEqual(self.cli("show", "99")[0], 3)
        target = os.path.join(self.tmp.name, "b.json")
        self.assertEqual(self.cli("backup", target)[0], 0)
        self.assertEqual(self.cli("backup", target)[0], 5)


if __name__ == "__main__":
    unittest.main()

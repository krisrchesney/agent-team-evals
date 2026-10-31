import io
import json
import os
import tempfile
import unittest

from tasklog import main
from tasklog.clock import FixedClock


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = os.path.join(self.tmp.name, "tasks.json")
        self.clock = FixedClock()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = main(["--store", self.store, *argv], stdout=out, stderr=err, clock=self.clock)
        return code, out.getvalue(), err.getvalue()

    def test_add_and_list(self):
        code, out, _ = self.run_cli("add", "Buy milk", "--project", "home", "--due", "2026-03-05")
        self.assertEqual((code, out), (0, "added task #1: Buy milk\n"))
        code, out, _ = self.run_cli("list", "--json")
        data = json.loads(out)
        self.assertEqual((code, data["command"], data["count"]), (0, "list", 1))
        self.assertEqual(data["items"][0]["due"], "2026-03-05")
        self.assertEqual(data["items"][0]["created"], "2026-03-02T09:00:00Z")

    def test_show_missing_task(self):
        code, out, err = self.run_cli("show", "7")
        self.assertEqual((code, out), (3, ""))
        self.assertEqual(err, "tasklog: error: no task #7\n")

    def test_done_twice_conflicts(self):
        self.run_cli("add", "Buy milk")
        self.assertEqual(self.run_cli("done", "1")[0], 0)
        self.assertEqual(self.run_cli("done", "1")[0], 5)

    def test_usage_errors(self):
        self.assertEqual(self.run_cli("add", "x", "--priority", "9")[0], 2)
        self.assertEqual(self.run_cli("list", "--status", "weird")[0], 2)
        self.assertEqual(self.run_cli("nonsense")[0], 2)

    def test_empty_list_warns(self):
        code, out, err = self.run_cli("list")
        self.assertEqual((code, out, err), (0, "", "tasklog: warning: no tasks match\n"))

    def test_backup_refuses_to_overwrite(self):
        self.run_cli("add", "Buy milk")
        target = os.path.join(self.tmp.name, "copy.json")
        self.assertEqual(self.run_cli("backup", target)[0], 0)
        self.assertEqual(self.run_cli("backup", target)[0], 5)
        self.assertEqual(self.run_cli("backup", target, "--force")[0], 0)


if __name__ == "__main__":
    unittest.main()

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from csvreport.cli import main
from csvreport.reader import read_rows


class TestReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sales.csv")
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            f.write("region,amount\nSouth,5\nNorth,10\nNorth,2.5\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_rows(self):
        rows = read_rows(self.path)
        self.assertEqual(rows[0]["region"], "South")
        self.assertEqual(len(rows), 3)

    def test_sum_by_group(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([self.path, "--group-by", "region", "--sum", "amount"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines(),
                         ["region,sum_amount", "North,12.50", "South,5.00"])


if __name__ == "__main__":
    unittest.main()

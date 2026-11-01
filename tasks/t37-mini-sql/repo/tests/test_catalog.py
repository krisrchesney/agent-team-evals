import os
import tempfile
import unittest

from minisql import Catalog, CatalogError


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write(self, name, text):
        with open(os.path.join(self._tmp.name, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    def test_types_and_nulls(self):
        self.write("People.csv", "id,Name,score\n1,Ann,2.5\n2,,3\n3,Bob,\n")
        t = Catalog(self._tmp.name).table("people")
        self.assertEqual(t.columns, ["id", "Name", "score"])
        self.assertEqual(t.rows, [(1, "Ann", 2.5), (2, None, 3.0), (3, "Bob", None)])

    def test_bad_field_count(self):
        self.write("t.csv", "a,b\n1\n")
        with self.assertRaises(CatalogError):
            Catalog(self._tmp.name).table("t")

    def test_missing_table(self):
        with self.assertRaises(CatalogError):
            Catalog(self._tmp.name).table("nope")

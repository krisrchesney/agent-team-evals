import unittest

from exportkit import export

RECORDS = [
    {"name": "Ann", "score": 9.5, "active": True},
    {"name": "Bob", "score": 7, "active": False},
]


class TestExport(unittest.TestCase):
    def test_csv(self):
        self.assertEqual(export(RECORDS, "csv"), "name,score,active\nAnn,9.5,true\nBob,7,false\n")

    def test_json_columns_subset(self):
        out = export(RECORDS, "json", columns=["name"], limit=1)
        self.assertEqual(out, '[\n  {\n    "name": "Ann"\n  }\n]')

    def test_table_sorted(self):
        out = export(RECORDS, "table", columns=["name", "score"], sort_by="score")
        self.assertEqual(out.splitlines()[2:], ["Bob       7", "Ann    9.50"])

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            export(RECORDS, "xml")


if __name__ == "__main__":
    unittest.main()

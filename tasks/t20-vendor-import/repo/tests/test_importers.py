import datetime
import unittest
from pathlib import Path

import ingest

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def sample(name):
    return (SAMPLES / name).read_text(encoding="utf-8")


class AcmeTests(unittest.TestCase):
    def test_sample(self):
        result = ingest.run_import("acme", sample("acme_2024-05.csv"))
        self.assertEqual(result.errors, [])
        first, second, third = result.records
        self.assertEqual((first.sku, first.unit_cents), ("AB100", 450))
        self.assertEqual(second.unit_cents, 125000)
        self.assertEqual(second.due_date, datetime.date(2024, 6, 1))
        self.assertEqual((third.description, third.currency), ("Rubber foot", "USD"))


class BoltTests(unittest.TestCase):
    def test_sample(self):
        result = ingest.run_import("bolt", sample("bolt_2024-05.tsv"))
        self.assertEqual(result.errors, [])
        self.assertEqual([r.sku for r in result.records], ["P1", "P2"])
        self.assertEqual(result.records[0].due_date, datetime.date(2024, 5, 17))


if __name__ == "__main__":
    unittest.main()

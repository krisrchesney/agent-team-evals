import unittest

from salesrep import ParseError, build_report

CSV = """id,date,region,product,qty,unit_price,discount_pct,currency,status
1,2024-01-05,East,Widget,2,10.00,0,USD,paid
2,2024-01-09,west,Gadget,1,100.00,10,EUR,paid
3,2024-02-01,East,Widget,3,5.50,,,
4,2024-02-02,West,Gadget,1,9.99,0,USD,void
5,2024-02-03,East,Widget,0,5.50,0,USD,paid
"""


class TestReport(unittest.TestCase):
    def test_table(self):
        out, issues = build_report(CSV)
        self.assertTrue(out.splitlines()[0].startswith("Region"))
        self.assertIn("36.50", out)
        self.assertEqual(len(issues), 1)

    def test_missing_column(self):
        with self.assertRaises(ParseError):
            build_report("id,date\n1,2024-01-01\n")


if __name__ == "__main__":
    unittest.main()

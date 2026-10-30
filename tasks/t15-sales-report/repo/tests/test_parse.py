import unittest
from datetime import date
from decimal import Decimal

from salesrep.dates import month_key, parse_iso
from salesrep.errors import ParseError
from salesrep.labels import label_key, tidy
from salesrep.parse import parse_text

HEADER = "id,date,region,product,qty,unit_price,discount_pct,currency,status"


class TestParse(unittest.TestCase):
    def test_defaults_and_normalising(self):
        txns, issues = parse_text([HEADER.split(",discount")[0], "a1, 2024-03-09 ,East,Pen,2,1.50"])
        self.assertEqual(issues, [])
        t = txns[0]
        self.assertEqual((t.id, t.date, t.qty, t.unit_price), ("a1", date(2024, 3, 9), 2, Decimal("1.50")))
        self.assertEqual((t.discount_pct, t.currency, t.status), (Decimal("0"), "USD", "paid"))

    def test_issue_line_numbers_count_blank_lines(self):
        txns, issues = parse_text([HEADER, "", "a,2024-13-01,E,P,1,1,0,usd,PAID", "b,2024-01-01,E,P,x,1,0,,"])
        self.assertEqual([(i.line, i.message) for i in issues],
                         [(3, "bad date '2024-13-01'"), (4, "bad quantity 'x'")])
        self.assertEqual(txns, [])

    def test_empty_input(self):
        with self.assertRaises(ParseError):
            parse_text([])

    def test_helpers(self):
        self.assertEqual(parse_iso("2024-02-29"), date(2024, 2, 29))
        self.assertEqual(month_key(date(2024, 3, 9)), 202403)
        self.assertEqual(tidy("  North   East "), "North East")
        self.assertEqual(label_key("North  EAST"), "north east")


if __name__ == "__main__":
    unittest.main()

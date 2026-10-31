import io
import unittest

from books import money
from books.errors import Unbalanced
from books.ledger import Ledger


def line(account, amount):
    return {"account": account, "amount": amount}


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.led = Ledger()
        for code, name, kind in [("1000", "Cash", "asset"), ("1200", "Receivable", "asset"),
                                 ("2000", "Tax payable", "liability"), ("3000", "Capital", "equity"),
                                 ("4000", "Sales", "income"), ("5000", "Rent", "expense")]:
            self.led.create_account(code, name, kind)
        self.led.post("2026-01-02", "capital", [line("1000", "1000.00"), line("3000", "-1000.00")])

    def test_money_round_trip(self):
        self.assertEqual(money.parse_amount("12.5"), 1250)
        self.assertEqual(money.format_amount(123456), "$1,234.56")
        self.assertEqual(money.percent(1999, 825), 165)

    def test_unbalanced_entry_is_rejected(self):
        with self.assertRaises(Unbalanced):
            self.led.post("2026-01-03", "oops", [line("1000", "5.00"), line("4000", "-4.00")])

    def test_trial_balance(self):
        self.led.post("2026-01-05", "rent", [line("5000", "300.00"), line("1000", "-300.00")])
        tb = self.led.reports.trial_balance()
        self.assertEqual((tb["total_debit"], tb["total_credit"], tb["balanced"]), (100000, 100000, True))

    def test_balance_sheet(self):
        self.led.post("2026-01-05", "sale", [line("1000", "50.00"), line("4000", "-50.00")])
        bs = self.led.reports.balance_sheet("2026-01-31")
        self.assertEqual(bs["assets"]["total"], 105000)
        self.assertEqual(bs["equity"]["rows"][-1]["account"], "current-earnings")
        self.assertTrue(bs["balanced"])

    def test_statement_running_balance(self):
        self.led.post("2026-01-05", "sale", [line("1000", "50.00"), line("4000", "-50.00")])
        st = self.led.reports.statement("1000", start="2026-01-03")
        self.assertEqual((st["opening"], st["closing"]), (100000, 105000))
        self.assertEqual(st["lines"][0]["display"], "$1,050.00")

    def test_budget_status(self):
        self.led.budgets.set("5000", "2026-01", "400.00")
        self.led.post("2026-01-05", "rent", [line("5000", "320.00"), line("1000", "-320.00")])
        status = self.led.budgets.status("5000", "2026-01")
        self.assertEqual((status["spent"], status["percent"], status["over"]), (32000, 80, False))
        self.assertEqual(len(self.led.budgets.alerts("2026-01")), 1)

    def test_invoice_lifecycle(self):
        inv = self.led.invoices.issue("INV-1", "Acme", "2026-01-10",
                                      [{"description": "Widget", "quantity": 3, "unit_price": "19.99"}],
                                      receivable="1200", revenue="4000", tax_bp=825, tax_account="2000")
        self.assertEqual((inv["subtotal"], inv["tax"], inv["total"]), (5997, 495, 6492))
        part = self.led.invoices.pay("INV-1", "2026-01-20", "30.00", bank="1000")
        self.assertEqual((part["status"], part["outstanding"]), ("partial", 3492))
        self.assertEqual(self.led.invoices.aging("2026-03-15")["31-60"], 3492)

    def test_recurring_posts_month_ends(self):
        self.led.recurring.add("rent", "2026-01-31", [line("5000", "300.00"), line("1000", "-300.00")], count=3)
        self.assertEqual(len(self.led.recurring.run("2026-12-31")), 3)
        self.assertEqual(self.led.journal.lines("5000")[1][0].date.isoformat(), "2026-02-28")

    def test_interest_accrual(self):
        out = self.led.interest.accrue("1000", 3650, "2026-02-01", "2026-02-11", "4000")
        self.assertEqual(out["interest"], 1000)
        self.assertEqual(out["display"], "$10.00")

    def test_reconcile(self):
        self.led.post("2026-01-05", "rent", [line("5000", "300.00"), line("1000", "-300.00")])
        res = self.led.reconciler.match("1000", [{"date": "2026-01-06", "amount": "-300.00"},
                                                 {"date": "2026-01-02", "amount": "1000.00"},
                                                 {"date": "2026-01-09", "amount": "-1.00"}])
        self.assertEqual(len(res["matched"]), 2)
        self.assertEqual(res["unmatched_statement"], [2])

    def test_csv_round_trip(self):
        self.led.post("2026-01-05", "sale", [line("1000", "50.25"), line("4000", "-50.25")])
        from books import csvio
        out = io.StringIO()
        csvio.export_entries(self.led.journal, out)
        self.assertIn("e2,2026-01-05,sale,1000,50.25", out.getvalue())
        other = Ledger()
        for a in self.led.chart.all():
            other.create_account(a.code, a.name, a.kind)
        self.assertEqual(len(csvio.import_entries(other.journal, io.StringIO(out.getvalue()))), 2)
        self.assertEqual(other.journal.balance("1000"), 105025)

    def test_snapshot_round_trip(self):
        copy = Ledger.load(self.led.dump())
        self.assertEqual(copy.journal.balance("1000"), 100000)
        self.assertEqual(copy.summary()["net_worth"], 100000)


if __name__ == "__main__":
    unittest.main()

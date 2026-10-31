"""Hidden tests for t30-multi-currency. Test names carry the requirement number; see AUDIT.md."""
import io
import json
import unittest
from decimal import Decimal

from books import csvio, money
from books.errors import (CurrencyMismatch, InvalidAmount, InvalidRate, InvoiceError, NoRate, Unbalanced,
                          UnknownCurrency)
from books.ledger import Ledger

ACCOUNTS = [
    ("1000", "Cash USD", "asset", "USD"), ("1100", "Cash EUR", "asset", "EUR"),
    ("1110", "Cash JPY", "asset", "JPY"), ("1120", "Cash KWD", "asset", "KWD"),
    ("1200", "AR USD", "asset", "USD"), ("1210", "AR EUR", "asset", "EUR"), ("1220", "AR JPY", "asset", "JPY"),
    ("2000", "Tax USD", "liability", "USD"), ("2100", "Tax EUR", "liability", "EUR"),
    ("2200", "Tax JPY", "liability", "JPY"), ("2300", "Loan USD", "liability", "USD"),
    ("2400", "Loan USD 2", "liability", "USD"),
    ("3000", "Capital USD", "equity", "USD"), ("3100", "Capital EUR", "equity", "EUR"),
    ("3200", "Capital JPY", "equity", "JPY"), ("3300", "Capital KWD", "equity", "KWD"),
    ("4000", "Sales USD", "income", "USD"), ("4100", "Sales EUR", "income", "EUR"),
    ("4200", "Sales JPY", "income", "JPY"),
    ("5000", "Rent USD", "expense", "USD"), ("5100", "Rent EUR", "expense", "EUR"),
    ("5200", "Rent JPY", "expense", "JPY"),
    ("6000", "Misc USD", "asset", "USD"), ("6100", "Misc USD 2", "asset", "USD"),
]


def L(account, amount, currency=None):
    line = {"account": account, "amount": amount}
    if currency:
        line["currency"] = currency
    return line


def new_ledger():
    led = Ledger()
    for code, name, kind, cur in ACCOUNTS:
        led.create_account(code, name, kind, cur)
    led.rates.set("EUR", "USD", "1.10", "2026-01-01")
    led.rates.set("EUR", "USD", "1.20", "2026-02-01")
    led.rates.set("USD", "JPY", "150", "2026-01-01")
    return led


class Base(unittest.TestCase):
    def setUp(self):
        self.led = new_ledger()

    def fund(self, account, capital, amount, date="2026-01-02"):
        self.led.post(date, "funding", [L(account, amount), L(capital, "-" + amount)])


class TestCurrencies(Base):
    def test_r1_exponents(self):
        for cur, digits in {"USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3}.items():
            self.assertEqual(money.EXPONENTS[cur], digits)

    def test_r1_parse(self):
        self.assertEqual(money.parse_amount("1500", "JPY"), 1500)
        self.assertEqual(money.parse_amount("12.345", "KWD"), 12345)
        self.assertEqual(money.parse_amount("12.50", "EUR"), 1250)
        self.assertEqual(money.parse_amount("1,234.5", "GBP"), 123450)
        self.assertEqual((money.parse_amount(7, "JPY"), money.parse_amount(7, "KWD"), money.parse_amount(7)),
                         (7, 7000, 700))

    def test_r1_too_many_decimals(self):
        for text, cur in [("15.5", "JPY"), ("1.234", "EUR"), ("1.2345", "KWD"), ("0.001", "USD")]:
            with self.assertRaises(InvalidAmount, msg=(text, cur)):
                money.parse_amount(text, cur)

    def test_r1_unknown_currency(self):
        with self.assertRaises(UnknownCurrency) as ctx:
            money.parse_amount("1", "XXX")
        self.assertEqual((ctx.exception.code, ctx.exception.param), ("unknown_currency", "currency"))
        with self.assertRaises(UnknownCurrency):
            self.led.create_account("9999", "Odd", "asset", "XYZ")
        with self.assertRaises(UnknownCurrency):
            money.format_amount(100, "XYZ")

    def test_r1_format(self):
        self.assertEqual(money.format_amount(123456), "$1,234.56")
        self.assertEqual(money.format_amount(-500), "-$5.00")
        self.assertEqual(money.format_amount(123456, "EUR"), "1,234.56 EUR")
        self.assertEqual(money.format_amount(-123456, "GBP"), "-1,234.56 GBP")
        self.assertEqual(money.format_amount(1234567, "JPY"), "1,234,567 JPY")
        self.assertEqual(money.format_amount(1234567, "KWD"), "1,234.567 KWD")
        self.assertEqual(money.format_amount(5, "KWD"), "0.005 KWD")

    def test_r1_decimal_string(self):
        self.assertEqual(money.to_decimal_string(-1500, "JPY"), "-1500")
        self.assertEqual(money.to_decimal_string(1250, "KWD"), "1.250")
        self.assertEqual(money.to_decimal_string(1250, "EUR"), "12.50")
        self.assertEqual(money.to_decimal_string(-5), "-0.05")

    def test_reg_percent_and_split(self):
        self.assertEqual(money.percent(1999, 825), 165)
        self.assertEqual(money.percent(-1999, 825), -165)
        self.assertEqual(money.split_evenly(100, 3), [34, 33, 33])


class TestAccountsAndPostings(Base):
    def test_r2_account_currency(self):
        self.assertEqual(self.led.chart.get("1110").currency, "JPY")
        self.assertEqual(self.led.create_account("7000", "New", "asset")["currency"], "USD")
        self.assertEqual(self.led.create_account("7100", "New EUR", "asset", "EUR")["currency"], "EUR")

    def test_r3_posting_view(self):
        out = self.led.post("2026-01-05", "seed", [L("1100", "100.00"), L("3100", "-100.00")])
        self.assertEqual([(p["account"], p["amount"], p["currency"]) for p in out["postings"]],
                         [("1100", 10000, "EUR"), ("3100", -10000, "EUR")])

    def test_r3_jpy_and_kwd_amounts(self):
        out = self.led.post("2026-01-05", "seed", [L("1110", "1500"), L("3200", "-1500")])
        self.assertEqual(out["postings"][0]["amount"], 1500)
        out = self.led.post("2026-01-05", "seed", [L("1120", "1.500"), L("3300", "-1.500")])
        self.assertEqual(out["postings"][0]["amount"], 1500)
        with self.assertRaises(InvalidAmount):
            self.led.post("2026-01-05", "bad", [L("1110", "15.5"), L("3200", "-15.5")])
        self.assertEqual(self.led.journal.balance("1110"), 1500)

    def test_r3_each_currency_must_balance(self):
        with self.assertRaises(Unbalanced):
            self.led.post("2026-01-05", "swap", [L("1100", "90.00"), L("1000", "-100.00")])
        with self.assertRaises(Unbalanced):
            self.led.post("2026-01-05", "swap", [L("1100", "100.00"), L("1000", "-100.00")])
        self.assertEqual(len(self.led.journal.entries), 0)

    def test_r3_mixed_entry_balanced_per_currency(self):
        out = self.led.post("2026-01-05", "exchange",
                            [L("1100", "100.00"), L("3100", "-100.00"), L("1000", "50.00"), L("3000", "-50.00")])
        self.assertEqual({p["currency"] for p in out["postings"]}, {"EUR", "USD"})

    def test_r3_line_currency_must_match_account(self):
        with self.assertRaises(CurrencyMismatch) as ctx:
            self.led.post("2026-01-05", "x", [L("1100", "1.00", "USD"), L("3100", "-1.00", "EUR")])
        self.assertEqual((ctx.exception.code, ctx.exception.param), ("currency_mismatch", "currency"))
        self.led.post("2026-01-05", "ok", [L("1100", "1.00", "EUR"), L("3100", "-1.00", "EUR")])
        self.assertEqual(len(self.led.journal.entries), 1)

    def test_r3_void_keeps_currency(self):
        first = self.led.post("2026-01-05", "seed", [L("1110", "1500"), L("3200", "-1500")])
        undo = self.led.void(first["id"], "2026-01-06")
        self.assertEqual([p["currency"] for p in undo["postings"]], ["JPY", "JPY"])
        self.assertEqual(self.led.journal.balance("1110"), 0)


class TestRates(Base):
    def test_r4_direct_rate_by_date(self):
        get = self.led.rates.get
        self.assertEqual(get("EUR", "USD", "2026-01-15"), Decimal("1.10"))
        self.assertEqual(get("EUR", "USD", "2026-02-01"), Decimal("1.20"))
        self.assertEqual(get("EUR", "USD"), Decimal("1.20"))
        with self.assertRaises(NoRate):
            get("EUR", "USD", "2025-12-31")

    def test_r4_inverse_and_identity(self):
        self.assertEqual(self.led.rates.get("USD", "EUR", "2026-01-15"), Decimal(1) / Decimal("1.10"))
        self.assertEqual(self.led.rates.get("JPY", "USD"), Decimal(1) / Decimal(150))
        self.assertEqual(self.led.rates.get("KWD", "KWD", "2026-01-15"), Decimal(1))

    def test_r4_no_rate(self):
        with self.assertRaises(NoRate) as ctx:
            self.led.rates.get("EUR", "JPY", "2026-01-15")
        self.assertEqual((ctx.exception.code, ctx.exception.param), ("no_rate", "currency"))

    def test_r4_direct_wins_over_inverse(self):
        self.led.rates.set("USD", "EUR", "0.90", "2026-01-01")
        self.assertEqual(self.led.rates.get("USD", "EUR", "2026-01-15"), Decimal("0.90"))

    def test_r4_convert_allows_for_decimals(self):
        convert = self.led.rates.convert
        self.assertEqual(convert(10000, "EUR", "USD", "2026-01-15"), 11000)
        self.assertEqual(convert(1000, "USD", "JPY", "2026-01-15"), 1500)       # $10.00 -> 1500 yen
        self.assertEqual(convert(1500, "JPY", "USD", "2026-01-15"), 1000)       # 1500 yen -> $10.00
        self.led.rates.set("USD", "KWD", "0.3075", "2026-01-01")
        self.assertEqual(convert(10000, "USD", "KWD", "2026-01-15"), 30750)     # $100.00 -> 30.750 KWD
        self.assertEqual(convert(500, "EUR", "EUR"), 500)

    def test_r4_rounds_half_away_from_zero(self):
        self.led.rates.set("EUR", "USD", "1.01", "2026-03-01")
        self.assertEqual(self.led.rates.convert(50, "EUR", "USD", "2026-03-05"), 51)
        self.assertEqual(self.led.rates.convert(-50, "EUR", "USD", "2026-03-05"), -51)

    def test_r4_invalid_rates(self):
        for bad in ("0", "-1", "abc"):
            with self.assertRaises(InvalidRate, msg=bad):
                self.led.rates.set("EUR", "KWD", bad, "2026-01-01")
        with self.assertRaises(InvalidRate):
            self.led.rates.set("EUR", "EUR", "1", "2026-01-01")
        with self.assertRaises(UnknownCurrency):
            self.led.rates.set("EUR", "XXX", "1", "2026-01-01")


class TestStatements(Base):
    def test_r5_trial_balance(self):
        self.fund("1100", "3100", "100.00")
        self.fund("1110", "3200", "3000")
        self.fund("1000", "3000", "50.00")
        tb = self.led.reports.trial_balance()
        self.assertEqual({r["account"]: r["currency"] for r in tb["rows"]},
                         {"1000": "USD", "1100": "EUR", "1110": "JPY", "3000": "USD", "3100": "EUR",
                          "3200": "JPY"})
        self.assertEqual(tb["totals"], {"USD": {"debit": 5000, "credit": 5000},
                                        "EUR": {"debit": 10000, "credit": 10000},
                                        "JPY": {"debit": 3000, "credit": 3000}})
        self.assertEqual((tb["total_debit"], tb["total_credit"], tb["balanced"]), (5000, 5000, True))

    def test_r5_no_usd_means_zero_usd_totals(self):
        self.fund("1100", "3100", "100.00")
        tb = self.led.reports.trial_balance()
        self.assertEqual((tb["total_debit"], tb["total_credit"]), (0, 0))
        self.assertEqual(tb["totals"], {"EUR": {"debit": 10000, "credit": 10000}})

    def test_r6_balance_sheet_converts(self):
        self.fund("1100", "3100", "100.00")
        self.fund("1000", "3000", "50.00")
        bs = self.led.reports.balance_sheet("2026-01-31")
        self.assertEqual((bs["currency"], bs["assets"]["total"], bs["equity"]["total"]), ("USD", 16000, 16000))
        self.assertTrue(bs["balanced"])
        in_eur = self.led.reports.balance_sheet("2026-01-31", currency="EUR")
        self.assertEqual((in_eur["currency"], in_eur["assets"]["total"]), ("EUR", 14545))  # 10000 + 5000/1.10
        rows = {r["account"]: r["balance"] for r in in_eur["assets"]["rows"]}
        self.assertEqual(rows, {"1100": 10000, "1000": 4545})

    def test_r6_balance_sheet_uses_rate_on_as_of(self):
        self.fund("1100", "3100", "100.00")
        self.assertEqual(self.led.reports.balance_sheet("2026-01-15")["assets"]["total"], 11000)
        self.assertEqual(self.led.reports.balance_sheet("2026-02-15")["assets"]["total"], 12000)

    def test_r6_each_account_is_converted_on_its_own(self):
        self.fund("6000", "3000", "0.05")
        self.fund("6100", "3000", "0.05")
        bs = self.led.reports.balance_sheet("2026-01-31", currency="JPY")
        self.assertEqual(bs["assets"]["total"], 16)   # 8 + 8, not 15
        self.assertTrue(bs["balanced"])

    def test_r6_earnings_are_converted(self):
        self.led.post("2026-01-10", "sale", [L("1100", "100.00"), L("4100", "-100.00")])
        bs = self.led.reports.balance_sheet("2026-01-31")
        self.assertEqual([(r["account"], r["balance"]) for r in bs["equity"]["rows"]],
                         [("current-earnings", 11000)])
        self.assertTrue(bs["balanced"])

    def test_r6_income_statement(self):
        self.led.post("2026-01-10", "sale", [L("1100", "100.00"), L("4100", "-100.00")])
        self.led.post("2026-01-12", "rent", [L("5000", "20.00"), L("1000", "-20.00")])
        inc = self.led.reports.income_statement("2026-01-01", "2026-01-31")
        self.assertEqual((inc["currency"], inc["income"]["total"], inc["expenses"]["total"], inc["net"]),
                         ("USD", 11000, 2000, 9000))
        later = self.led.reports.income_statement("2026-01-01", "2026-02-28")
        self.assertEqual(later["income"]["total"], 12000)   # rate on the end date
        in_yen = self.led.reports.income_statement("2026-01-11", "2026-01-31", currency="JPY")
        self.assertEqual(in_yen["expenses"]["total"], 3000)

    def test_r6_statement_stays_in_account_currency(self):
        self.led.post("2026-01-05", "seed", [L("1110", "1500"), L("3200", "-1500")])
        self.led.post("2026-01-08", "more", [L("1110", "250"), L("3200", "-250")])
        st = self.led.reports.statement("1110", start="2026-01-06")
        self.assertEqual((st["currency"], st["opening"], st["closing"]), ("JPY", 1500, 1750))
        self.assertEqual(st["lines"][0]["display"], "1,750 JPY")
        kwd = self.led.reports
        self.led.post("2026-01-09", "k", [L("1120", "12.345"), L("3300", "-12.345")])
        self.assertEqual(kwd.statement("1120")["lines"][0]["display"], "12.345 KWD")

    def test_r14_summary_converts_each_account(self):
        self.led.post("2026-01-05", "loans", [L("6000", "0.05"), L("2300", "-0.05")])
        self.led.post("2026-01-05", "loans", [L("6100", "0.05"), L("2400", "-0.05")])
        s = self.led.summary(currency="JPY")
        self.assertEqual((s["currency"], s["assets"], s["liabilities"], s["net_worth"]), ("JPY", 16, 16, 0))
        usd = self.led.summary()
        self.assertEqual((usd["currency"], usd["assets"], usd["net_worth"]), ("USD", 10, 0))

    def test_r14_summary_uses_rate_on_as_of(self):
        self.fund("1100", "3100", "100.00")
        self.assertEqual(self.led.summary("2026-01-15")["assets"], 11000)
        self.assertEqual(self.led.summary("2026-02-15")["assets"], 12000)
        self.assertEqual((self.led.summary()["accounts"], self.led.summary()["entries"]), (len(ACCOUNTS), 1))


class TestBudgets(Base):
    def test_r7_defaults_to_account_currency(self):
        status = self.led.budgets.set("5100", "2026-01", "200.00")
        self.assertEqual((status["currency"], status["limit"]), ("EUR", 20000))
        self.led.post("2026-01-05", "rent", [L("5100", "160.00"), L("1100", "-160.00")])
        status = self.led.budgets.status("5100", "2026-01")
        self.assertEqual((status["spent"], status["percent"], status["over"]), (16000, 80, False))

    def test_r7_limit_is_parsed_in_the_budget_currency(self):
        self.assertEqual(self.led.budgets.set("5200", "2026-01", "50000")["limit"], 50000)
        with self.assertRaises(InvalidAmount):
            self.led.budgets.set("5200", "2026-02", "500.5")
        self.assertEqual(self.led.budgets.set("5100", "2026-02", "100", "JPY")["limit"], 100)

    def test_r7_converts_each_posting_at_its_own_date(self):
        self.led.rates.set("EUR", "USD", "1.30", "2026-02-15")
        self.led.budgets.set("5100", "2026-02", "300.00", "USD")
        self.led.post("2026-02-10", "rent", [L("5100", "100.00"), L("1100", "-100.00")])
        self.led.post("2026-02-20", "rent", [L("5100", "100.00"), L("1100", "-100.00")])
        status = self.led.budgets.status("5100", "2026-02")
        self.assertEqual((status["currency"], status["spent"], status["percent"]), ("USD", 25000, 83))

    def test_r7_alerts_use_each_budget_currency(self):
        self.led.budgets.set("5000", "2026-01", "100.00")
        self.led.budgets.set("5200", "2026-01", "1000")
        self.led.budgets.set("5100", "2026-01", "100.00")
        self.led.post("2026-01-05", "a", [L("5000", "85.00"), L("1000", "-85.00")])
        self.led.post("2026-01-05", "b", [L("5200", "950"), L("1110", "-950")])
        self.led.post("2026-01-05", "c", [L("5100", "10.00"), L("1100", "-10.00")])
        alerts = self.led.budgets.alerts("2026-01")
        self.assertEqual([(a["account"], a["currency"], a["percent"]) for a in alerts],
                         [("5200", "JPY", 95), ("5000", "USD", 85)])


class TestInvoices(Base):
    def issue(self, number="INV-1", currency_accounts=("1210", "4100", "2100"), unit="19.99", tax_bp=825,
              date="2026-01-10", qty=3):
        ar, rev, tax = currency_accounts
        return self.led.invoices.issue(number, "Acme", date, [{"description": "W", "quantity": qty,
                                                                  "unit_price": unit}],
                                       receivable=ar, revenue=rev, tax_bp=tax_bp, tax_account=tax)

    def test_r8_euro_invoice(self):
        inv = self.issue()
        self.assertEqual((inv["currency"], inv["subtotal"], inv["tax"], inv["total"]), ("EUR", 5997, 495, 6492))
        self.assertEqual(self.led.journal.balance("1210"), 6492)

    def test_r8_yen_invoice_uses_whole_units(self):
        inv = self.issue("INV-2", ("1220", "4200", "2200"), unit="1999", tax_bp=1000)
        self.assertEqual((inv["currency"], inv["lines"][0]["unit_price"], inv["subtotal"], inv["tax"],
                          inv["total"]), ("JPY", 1999, 5997, 600, 6597))
        self.assertEqual(self.led.journal.balance("1220"), 6597)
        self.assertEqual(self.led.journal.balance("4200"), -5997)
        with self.assertRaises(InvalidAmount):
            self.issue("INV-3", ("1220", "4200", "2200"), unit="19.99")

    def test_r8_other_accounts_must_share_the_currency(self):
        for accounts in [("1210", "4000", "2100"), ("1210", "4100", "2000")]:
            with self.assertRaises(CurrencyMismatch):
                self.issue("INV-9", accounts)
        self.assertEqual(self.led.journal.entries, [])
        self.assertEqual(self.issue("INV-9")["number"], "INV-9")   # the number was not used up

    def test_r8_payments_are_in_the_invoice_currency(self):
        self.issue()
        with self.assertRaises(CurrencyMismatch):
            self.led.invoices.pay("INV-1", "2026-01-20", "10.00", bank="1000")
        paid = self.led.invoices.pay("INV-1", "2026-01-20", "10.00", bank="1100")
        self.assertEqual((paid["status"], paid["paid"], paid["outstanding"]), ("partial", 1000, 5492))
        with self.assertRaises(InvoiceError):
            self.led.invoices.pay("INV-1", "2026-01-21", "100.00", bank="1100")
        yen = self.issue("INV-2", ("1220", "4200", "2200"), unit="1000", tax_bp=0)
        with self.assertRaises(InvalidAmount):
            self.led.invoices.pay("INV-2", "2026-01-20", "500.5", bank="1110")
        self.assertEqual(self.led.invoices.pay("INV-2", "2026-01-20", "3000", bank="1110")["status"], "paid")
        self.assertEqual(yen["total"], 3000)

    def test_r8_aging_converts_each_invoice(self):
        self.issue("EUR-1", unit="100.00", tax_bp=0, qty=1)                       # due 2026-02-09
        self.issue("JPY-1", ("1220", "4200", "2200"), unit="1500", tax_bp=0, qty=1, date="2026-03-01")
        self.led.invoices.issue("USD-1", "Acme", "2026-03-01", [{"quantity": 1, "unit_price": "10.00"}],
                                receivable="1200", revenue="4000")
        aging = self.led.invoices.aging("2026-03-15")
        self.assertEqual(aging["currency"], "USD")
        self.assertEqual((aging["current"], aging["1-30"], aging["31-60"], aging["61+"], aging["total"]),
                         (2000, 0, 12000, 0, 14000))

    def test_r8_aging_rounds_per_invoice_and_can_report_in_other_currencies(self):
        for n in (1, 2):
            self.issue(f"Y-{n}", ("1220", "4200", "2200"), unit="1", tax_bp=0, qty=1, date="2026-03-01")
        self.assertEqual(self.led.invoices.aging("2026-03-02")["total"], 2)          # 2 x 0.67 cents -> 1 + 1
        in_yen = self.led.invoices.aging("2026-03-02", currency="JPY")
        self.assertEqual((in_yen["currency"], in_yen["total"]), ("JPY", 2))


class TestRecurringAndInterest(Base):
    def test_r9_template_must_balance_per_currency(self):
        with self.assertRaises(Unbalanced):
            self.led.recurring.add("swap", "2026-01-31", [L("1100", "100.00"), L("1000", "-100.00")])
        with self.assertRaises(InvalidAmount):
            self.led.recurring.add("bad", "2026-01-31", [L("5200", "15.5"), L("1110", "-15.5")])
        self.led.recurring.add("ok", "2026-01-31", [L("5200", "1500"), L("1110", "-1500"),
                                                    L("5100", "10.00"), L("1100", "-10.00")], count=2)

    def test_r9_recurring_posts_in_each_currency(self):
        self.led.recurring.add("rent", "2026-01-31", [L("5200", "1500"), L("1110", "-1500")], count=2)
        ids = self.led.recurring.run("2026-12-31")
        self.assertEqual(len(ids), 2)
        self.assertEqual(self.led.journal.get(ids[1]).postings[0].currency, "JPY")
        self.assertEqual(self.led.journal.balance("1110"), -3000)

    def test_r10_interest_in_euro(self):
        self.fund("1100", "3100", "1000.00", "2026-01-31")
        out = self.led.interest.accrue("1100", 3650, "2026-02-01", "2026-02-11", "4100")
        self.assertEqual((out["currency"], out["interest"], out["display"]), ("EUR", 1000, "10.00 EUR"))
        self.assertEqual(self.led.journal.get(out["entry"]).postings[0].currency, "EUR")
        self.assertEqual(self.led.journal.balance("4100"), -1000)

    def test_r10_interest_in_yen(self):
        self.fund("1110", "3200", "100000", "2026-01-31")
        out = self.led.interest.accrue("1110", 3650, "2026-02-01", "2026-02-11", "4200")
        self.assertEqual((out["currency"], out["interest"], out["display"]), ("JPY", 1000, "1,000 JPY"))
        self.assertEqual(self.led.journal.balance("1110"), 101000)

    def test_r10_income_account_must_share_the_currency(self):
        self.fund("1100", "3100", "1000.00", "2026-01-31")
        with self.assertRaises(CurrencyMismatch):
            self.led.interest.accrue("1100", 3650, "2026-02-01", "2026-02-11", "4000")
        self.assertEqual(len(self.led.journal.entries), 1)

    def test_reg_interest_in_usd(self):
        self.fund("1000", "3000", "1000.00", "2026-01-31")
        out = self.led.interest.accrue("1000", 3650, "2026-02-01", "2026-02-11", "4000")
        self.assertEqual((out["interest"], out["display"]), (1000, "$10.00"))


class TestReconcile(Base):
    def test_r11_yen_statement(self):
        self.led.post("2026-01-05", "seed", [L("1110", "1500"), L("3200", "-1500")])
        res = self.led.reconciler.match("1110", [{"date": "2026-01-06", "amount": "1505"}], tolerance="10")
        self.assertEqual(res["currency"], "JPY")
        self.assertEqual([(m["statement"], m["difference"]) for m in res["matched"]], [(0, 5)])
        self.assertEqual(res["display"], {"statement": "1,505 JPY", "ledger": "1,500 JPY"})
        miss = self.led.reconciler.match("1110", [{"date": "2026-01-06", "amount": "1511"}], tolerance="10")
        self.assertEqual(miss["unmatched_statement"], [0])

    def test_r11_dinar_tolerance(self):
        self.led.post("2026-01-05", "seed", [L("1120", "2.500"), L("3300", "-2.500")])
        res = self.led.reconciler.match("1120", [{"date": "2026-01-05", "amount": "2.504"}], tolerance="0.005")
        self.assertEqual(len(res["matched"]), 1)
        self.assertEqual((res["matched"][0]["difference"], res["statement_total"], res["display"]["ledger"]),
                         (4, 2504, "2.500 KWD"))
        with self.assertRaises(InvalidAmount):
            self.led.reconciler.match("1120", [{"date": "2026-01-05", "amount": "2.5041"}])

    def test_reg_usd_reconcile(self):
        self.led.post("2026-01-05", "seed", [L("1000", "12.50"), L("3000", "-12.50")])
        res = self.led.reconciler.match("1000", [{"date": "2026-01-05", "amount": "12.50"}])
        self.assertEqual((len(res["matched"]), res["display"]["ledger"]), (1, "$12.50"))


class TestCsv(Base):
    def seed(self):
        self.led.post("2026-01-05", "yen", [L("1110", "1500"), L("3200", "-1500")])
        self.led.post("2026-01-06", "euro", [L("1100", "100.00"), L("3100", "-100.00")])
        self.led.post("2026-01-07", "dinar", [L("1120", "1.500"), L("3300", "-1.500")])

    def test_r12_export_has_a_currency_column(self):
        self.seed()
        out = io.StringIO()
        csvio.export_entries(self.led.journal, out)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], "entry,date,memo,account,amount,currency")
        self.assertIn("e1,2026-01-05,yen,1110,1500,JPY", lines)
        self.assertIn("e2,2026-01-06,euro,3100,-100.00,EUR", lines)
        self.assertIn("e3,2026-01-07,dinar,1120,1.500,KWD", lines)

    def test_r12_round_trip(self):
        self.seed()
        out = io.StringIO()
        csvio.export_entries(self.led.journal, out)
        other = new_ledger()
        self.assertEqual(len(csvio.import_entries(other.journal, io.StringIO(out.getvalue()))), 3)
        for code in ("1110", "1100", "1120", "3200"):
            self.assertEqual(other.journal.balance(code), self.led.journal.balance(code))

    def test_r12_import_older_file_without_currency(self):
        text = ("entry,date,memo,account,amount\n"
                "1,2026-01-05,yen,1110,1500\n1,2026-01-05,yen,3200,-1500\n"
                "2,2026-01-06,usd,1000,12.50\n2,2026-01-06,usd,3000,-12.50\n")
        self.assertEqual(len(csvio.import_entries(self.led.journal, io.StringIO(text))), 2)
        self.assertEqual((self.led.journal.balance("1110"), self.led.journal.balance("1000")), (1500, 1250))

    def test_r12_import_rejects_wrong_currency_and_bad_decimals(self):
        text = ("entry,date,memo,account,amount,currency\n"
                "1,2026-01-05,yen,1110,1500,USD\n1,2026-01-05,yen,3200,-1500,JPY\n")
        with self.assertRaises(CurrencyMismatch):
            csvio.import_entries(self.led.journal, io.StringIO(text))
        text = "entry,date,memo,account,amount\n1,2026-01-05,yen,1110,15.5\n1,2026-01-05,yen,3200,-15.5\n"
        with self.assertRaises(InvalidAmount) as ctx:
            csvio.import_entries(self.led.journal, io.StringIO(text))
        self.assertIn("row 2", ctx.exception.message)
        self.assertEqual(self.led.journal.entries, [])


class TestSnapshot(Base):
    def test_r13_round_trip_through_json(self):
        self.led.post("2026-01-05", "yen", [L("1110", "1500"), L("3200", "-1500")])
        self.led.post("2026-01-06", "euro", [L("1100", "100.00"), L("3100", "-100.00")])
        data = json.loads(json.dumps(self.led.dump()))
        self.assertEqual({a["code"]: a["currency"] for a in data["accounts"]}["1110"], "JPY")
        self.assertEqual([p["currency"] for p in data["entries"][1]["postings"]], ["EUR", "EUR"])
        copy = Ledger.load(data)
        self.assertEqual(copy.chart.get("1100").currency, "EUR")
        self.assertEqual((copy.journal.balance("1110"), copy.journal.balance("1100")), (1500, 10000))
        self.assertEqual(copy.journal.get("e2").postings[0].currency, "EUR")
        self.assertEqual(copy.rates.get("EUR", "USD", "2026-01-15"), Decimal("1.10"))
        self.assertEqual(copy.rates.get("EUR", "USD"), Decimal("1.20"))
        self.assertEqual(copy.rates.convert(1000, "USD", "JPY"), 1500)
        self.assertEqual(copy.reports.trial_balance()["totals"], self.led.reports.trial_balance()["totals"])

    def test_r13_older_dump_is_all_usd(self):
        old = {"version": 1,
               "accounts": [{"code": "1000", "name": "Cash", "kind": "asset"},
                            {"code": "3000", "name": "Capital", "kind": "equity"}],
               "entries": [{"id": "e1", "date": "2026-01-02", "memo": "capital", "ref": None, "voids": None,
                            "postings": [{"account": "1000", "amount": 5000},
                                         {"account": "3000", "amount": -5000}]}]}
        copy = Ledger.load(old)
        self.assertEqual(copy.chart.get("1000").currency, "USD")
        self.assertEqual(copy.journal.get("e1").postings[0].currency, "USD")
        self.assertEqual(copy.summary()["net_worth"], 5000)
        copy.post("2026-01-03", "more", [L("1000", "1.00"), L("3000", "-1.00")])
        self.assertEqual(copy.journal.balance("1000"), 5100)


class TestUsdUnchanged(Base):
    def test_reg_usd_flow(self):
        self.fund("1000", "3000", "1000.00")
        inv = self.led.invoices.issue("INV-1", "Acme", "2026-01-10",
                                      [{"description": "W", "quantity": 3, "unit_price": "19.99"}],
                                      receivable="1200", revenue="4000", tax_bp=825, tax_account="2000")
        self.assertEqual((inv["subtotal"], inv["tax"], inv["total"]), (5997, 495, 6492))
        tb = self.led.reports.trial_balance()
        self.assertEqual((tb["total_debit"], tb["total_credit"], tb["balanced"]), (106492, 106492, True))
        st = self.led.reports.statement("1000")
        self.assertEqual(st["lines"][0]["display"], "$1,000.00")
        self.assertEqual(self.led.summary()["net_worth"], 106492 - 495)


if __name__ == "__main__":
    unittest.main()

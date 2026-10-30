"""Hidden tests for t21. Each test name names the rule it checks:
s<N> = docs/STATEMENTS.md rule N, feed = docs/FEED.md, report = a complaint in the prompt,
reg = existing behaviour that must keep working.
"""
import datetime
import unittest

from stmt import Account, Txn, TxnStore, build_statement, render
from stmt.export import to_csv

UTC = datetime.timezone.utc
TOKYO = Account("keiko", "Keiko", 540)
NEW_YORK = Account("ny", "Nia", -300)
LONDON = Account("dan", "Dan", 0)


def at(*args):
    return datetime.datetime(*args, tzinfo=UTC)


def ids(statement):
    return [t.external_id for t in statement.lines]


def line_for(text, description):
    return next(line for line in text.splitlines() if description in line)


class Keiko(unittest.TestCase):
    def setUp(self):
        self.store = TxnStore([
            Txn("salary", "keiko", 300000, at(2024, 4, 24, 0), "Salary"),
            Txn("coffee", "keiko", -450, at(2024, 4, 30, 22, 15), "Coffee"),        # 07:15 May 1 Tokyo
            Txn("rent", "keiko", -120000, at(2024, 5, 31, 1), "Rent"),             # 10:00 May 31
            Txn("dinner", "keiko", -6800, at(2024, 5, 31, 12, 30), "Dinner"),      # 21:30 May 31
            Txn("taxi", "keiko", -2100, at(2024, 5, 31, 14, 59, 59), "Taxi"),      # 23:59:59 May 31
            Txn("bakery", "keiko", -380, at(2024, 5, 31, 15, 0), "Bakery"),         # 00:00 June 1
        ])

    def test_report_may_includes_all_of_may_31(self):
        may = build_statement(self.store, TOKYO, 2024, 5)
        self.assertEqual(ids(may), ["coffee", "rent", "dinner", "taxi"])

    def test_report_april_ends_before_may_1_local(self):
        april = build_statement(self.store, TOKYO, 2024, 4)
        self.assertEqual(ids(april), ["salary"])

    def test_s1_june_starts_at_local_midnight(self):
        self.assertEqual(ids(build_statement(self.store, TOKYO, 2024, 6)), ["bakery"])

    def test_s3_balances_follow_the_local_period(self):
        april = build_statement(self.store, TOKYO, 2024, 4)
        may = build_statement(self.store, TOKYO, 2024, 5)
        june = build_statement(self.store, TOKYO, 2024, 6)
        self.assertEqual((april.opening_cents, april.closing_cents), (0, 300000))
        self.assertEqual((may.opening_cents, may.closing_cents), (300000, 300000 - 450 - 120000 - 6800 - 2100))
        self.assertEqual((june.opening_cents, june.closing_cents), (may.closing_cents, may.closing_cents - 380))

    def test_s5_dates_are_local(self):
        text = render(build_statement(self.store, TOKYO, 2024, 5))
        self.assertIn("2024-05-01", line_for(text, "Coffee"))
        self.assertIn("2024-05-31", line_for(text, "Taxi"))
        self.assertIn("2024-06-01", line_for(render(build_statement(self.store, TOKYO, 2024, 6)), "Bakery"))


class OtherZones(unittest.TestCase):
    def test_s1_utc_account_keeps_the_whole_last_day(self):
        store = TxnStore([
            Txn("a", "dan", -100, at(2024, 5, 31, 0, 0), "A"),
            Txn("b", "dan", -200, at(2024, 5, 31, 23, 59, 59), "B"),
            Txn("c", "dan", -300, at(2024, 6, 1, 0, 0), "C"),
            Txn("d", "dan", -400, at(2024, 5, 1, 0, 0), "D"),
        ])
        self.assertEqual(ids(build_statement(store, LONDON, 2024, 5)), ["d", "a", "b"])
        self.assertEqual(ids(build_statement(store, LONDON, 2024, 6)), ["c"])

    def test_s1_negative_offset(self):
        store = TxnStore([
            Txn("late", "ny", -100, at(2024, 6, 1, 3, 0), "Late"),      # 22:00 May 31 New York
            Txn("early", "ny", -200, at(2024, 5, 1, 4, 59), "Early"),   # 23:59 Apr 30 New York
            Txn("first", "ny", -300, at(2024, 5, 1, 5, 0), "First"),    # 00:00 May 1 New York
        ])
        self.assertEqual(ids(build_statement(store, NEW_YORK, 2024, 5)), ["first", "late"])
        self.assertEqual(ids(build_statement(store, NEW_YORK, 2024, 4)), ["early"])
        text = render(build_statement(store, NEW_YORK, 2024, 5))
        self.assertIn("2024-05-31", line_for(text, "Late"))

    def test_s1_year_end_and_february(self):
        store = TxnStore([
            Txn("nye", "dan", -100, at(2024, 12, 31, 23, 0), "NYE"),
            Txn("ny", "dan", -200, at(2025, 1, 1, 0, 0), "New year"),
            Txn("leap", "dan", -300, at(2024, 2, 29, 12, 0), "Leap day"),
            Txn("mar", "dan", -400, at(2024, 3, 1, 0, 0), "March"),
        ])
        self.assertEqual(ids(build_statement(store, LONDON, 2024, 12)), ["nye"])
        self.assertEqual(ids(build_statement(store, LONDON, 2025, 1)), ["ny"])
        self.assertEqual(ids(build_statement(store, LONDON, 2024, 2)), ["leap"])
        tokyo = TxnStore([Txn("x", "keiko", -1, at(2024, 12, 31, 15, 0), "X")])   # 00:00 Jan 1 Tokyo
        self.assertEqual(ids(build_statement(tokyo, TOKYO, 2025, 1)), ["x"])
        self.assertEqual(ids(build_statement(tokyo, TOKYO, 2024, 12)), [])

    def test_s1_half_hour_offset(self):
        india = Account("in", "Ira", 330)
        store = TxnStore([Txn("x", "in", -1, at(2024, 5, 31, 18, 29), "X"),   # 23:59 May 31
                          Txn("y", "in", -1, at(2024, 5, 31, 18, 30), "Y")])  # 00:00 June 1
        self.assertEqual(ids(build_statement(store, india, 2024, 5)), ["x"])


class Dan(unittest.TestCase):
    def setUp(self):
        self.store = TxnStore([
            Txn("pay", "dan", 200000, at(2024, 4, 25, 9), "Salary"),
            Txn("p1", "dan", -5000, at(2024, 5, 2, 10), "AMZN MKTP 7731", version=1),
            Txn("p1", "dan", -5000, at(2024, 5, 2, 10), "Amazon", version=2),
            Txn("p2", "dan", -1999, at(2024, 5, 5, 18), "Cinema"),
        ])

    def test_report_amended_payment_shows_once(self):
        may = build_statement(self.store, LONDON, 2024, 5)
        self.assertEqual(ids(may), ["p1", "p2"])
        self.assertEqual(may.lines[0].description, "Amazon")
        self.assertEqual(may.closing_cents, 200000 - 5000 - 1999)

    def test_feed_latest_version_wins_even_if_it_arrives_out_of_order(self):
        store = TxnStore([
            Txn("p1", "dan", -800, at(2024, 5, 2, 10), "Fuel (final)", version=3),
            Txn("p1", "dan", -1000, at(2024, 5, 2, 10), "Fuel (pre-auth)", version=1),
            Txn("p1", "dan", -900, at(2024, 5, 2, 10), "Fuel", version=2),
        ])
        may = build_statement(store, LONDON, 2024, 5)
        self.assertEqual([(t.description, t.amount_cents) for t in may.lines], [("Fuel (final)", -800)])
        self.assertEqual(may.closing_cents, -800)

    def test_s2_opening_balance_counts_each_transaction_once(self):
        self.store.add(Txn("pay", "dan", 200000, at(2024, 4, 25, 9), "Salary ACME LTD", version=2))
        may = build_statement(self.store, LONDON, 2024, 5)
        self.assertEqual(may.opening_cents, 200000)
        april = build_statement(self.store, LONDON, 2024, 4)
        self.assertEqual((ids(april), april.closing_cents), (["pay"], 200000))

    def test_s2_corrected_amount_uses_the_latest(self):
        self.store.add(Txn("p2", "dan", -1499, at(2024, 5, 5, 18), "Cinema (discount)", version=2))
        may = build_statement(self.store, LONDON, 2024, 5)
        self.assertEqual(may.closing_cents, 200000 - 5000 - 1499)
        self.assertIn("-14.99", render(may))
        self.assertNotIn("-19.99", render(may))

    def test_s2_settled_time_can_move_a_transaction_to_another_month(self):
        store = TxnStore([
            Txn("m", "dan", -700, at(2024, 5, 31, 22), "Hotel", version=1),
            Txn("m", "dan", -700, at(2024, 6, 2, 8), "Hotel", version=2),
        ])
        may, june = build_statement(store, LONDON, 2024, 5), build_statement(store, LONDON, 2024, 6)
        self.assertEqual((ids(may), may.closing_cents), ([], 0))
        self.assertEqual((ids(june), june.opening_cents, june.closing_cents), (["m"], 0, -700))

    def test_s2_pending_status_follows_the_latest_version(self):
        store = TxnStore([
            Txn("a", "dan", -100, at(2024, 5, 3), "Was pending", version=1, status="pending"),
            Txn("a", "dan", -100, at(2024, 5, 3), "Was pending", version=2, status="posted"),
            Txn("b", "dan", -200, at(2024, 5, 4), "Back to pending", version=1, status="posted"),
            Txn("b", "dan", -200, at(2024, 5, 4), "Back to pending", version=2, status="pending"),
            Txn("c", "dan", -300, at(2024, 4, 4), "Old, now pending", version=1, status="posted"),
            Txn("c", "dan", -300, at(2024, 4, 4), "Old, now pending", version=2, status="pending"),
        ])
        may = build_statement(store, LONDON, 2024, 5)
        self.assertEqual((ids(may), may.opening_cents, may.closing_cents), (["a"], 0, -100))

    def test_s2_export_has_one_row_per_transaction(self):
        rows = to_csv(build_statement(self.store, LONDON, 2024, 5)).splitlines()
        self.assertEqual(len(rows), 3)
        self.assertIn("Amazon", rows[1])


class Continuity(unittest.TestCase):
    def test_s3_closing_equals_next_opening_across_a_year(self):
        store = TxnStore()
        n = 0
        for month in range(1, 13):
            for day, hour, amount in ((1, 0, 1000), (15, 12, -333), (28, 23, -77)):
                n += 1
                store.add(Txn(f"t{n}", "keiko", amount, at(2024, month, day, hour), f"T{n}"))
                if n % 4 == 0:
                    store.add(Txn(f"t{n}", "keiko", amount - 1, at(2024, month, day, hour), f"T{n}*", version=2))
        for account in (TOKYO, Account("keiko", "Keiko UTC", 0), Account("keiko", "Keiko NY", -300)):
            previous = None
            for month in range(1, 13):
                statement = build_statement(store, account, 2024, month)
                if previous is not None:
                    self.assertEqual(statement.opening_cents, previous.closing_cents, (account.name, month))
                self.assertEqual(statement.closing_cents,
                                 statement.opening_cents + sum(t.amount_cents for t in statement.lines))
                previous = statement

    def test_s4_order_by_time_then_external_id(self):
        store = TxnStore([Txn("b", "dan", -1, at(2024, 5, 2, 9)), Txn("a", "dan", -1, at(2024, 5, 2, 9)),
                          Txn("c", "dan", -1, at(2024, 5, 1, 9))])
        self.assertEqual(ids(build_statement(store, LONDON, 2024, 5)), ["c", "a", "b"])


class Regression(unittest.TestCase):
    def test_reg_render_layout(self):
        store = TxnStore([Txn("t", "dan", -2500, at(2024, 5, 3, 12), "Groceries")])
        text = render(build_statement(store, LONDON, 2024, 5))
        self.assertEqual(text.splitlines()[0], "Statement for Dan (dan), 2024-05")
        self.assertEqual(text.splitlines()[1], "Opening balance: 0.00")
        self.assertTrue(text.endswith("Closing balance: -25.00\n"))
        self.assertEqual(render(build_statement(store, LONDON, 2024, 7)).splitlines()[2], "(no transactions)")

    def test_reg_store_keeps_history(self):
        store = TxnStore([Txn("x", "dan", -1, at(2024, 5, 1), version=1), Txn("x", "dan", -2, at(2024, 5, 1), version=2)])
        self.assertEqual(len(store.all("dan")), 2)
        self.assertEqual([t.amount_cents for t in store.current("dan")], [-2])


if __name__ == "__main__":
    unittest.main()

import datetime
import unittest

from stmt import Account, Txn, TxnStore, build_statement, render

UTC = datetime.timezone.utc


def at(*args):
    return datetime.datetime(*args, tzinfo=UTC)


class StatementTests(unittest.TestCase):
    def test_simple_month(self):
        acct = Account("a1", "Ann")
        store = TxnStore([
            Txn("t1", "a1", 10000, at(2024, 4, 20, 9), "Salary"),
            Txn("t2", "a1", -2500, at(2024, 5, 3, 12), "Groceries"),
            Txn("t3", "a1", -1000, at(2024, 5, 10, 8), "Pending thing", status="pending"),
        ])
        statement = build_statement(store, acct, 2024, 5)
        self.assertEqual(statement.opening_cents, 10000)
        self.assertEqual([t.external_id for t in statement.lines], ["t2"])
        self.assertEqual(statement.closing_cents, 7500)
        self.assertIn("Closing balance: 75.00", render(statement))


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date

from billkit import Billing
from billkit.errors import Conflict, ValidationError


class BillingTest(unittest.TestCase):
    def setUp(self):
        self.app = Billing()
        self.app.catalog.add("team", "Team", "month", 3000, included_units=300)
        self.cus = self.app.customers.create(name="Acme", email="a@acme.test")

    def test_full_first_period(self):
        sub = self.app.subscribe(self.cus.id, "team", date(2026, 4, 1), quantity=2)
        (inv,) = self.app.invoices.for_subscription(sub.id)
        self.assertEqual(inv.subtotal_cents, 6000)
        self.assertEqual(inv.lines[0].kind, "subscription")

    def test_partial_first_period_in_a_30_day_month(self):
        sub = self.app.subscribe(self.cus.id, "team", date(2026, 4, 11))
        (inv,) = self.app.invoices.for_subscription(sub.id)
        self.assertEqual(inv.lines[0].amount_cents, 2000)
        self.assertEqual(inv.lines[0].kind, "proration")

    def test_plan_change_in_a_30_day_month(self):
        self.app.catalog.add("big", "Big", "month", 9000)
        sub = self.app.subscribe(self.cus.id, "team", date(2026, 4, 1))
        change = self.app.change_plan(sub.id, "big", date(2026, 4, 16))
        self.assertEqual((change.credit_cents, change.charge_cents, change.net_cents), (1500, 4500, 3000))

    def test_cancel_refunds_unused_days(self):
        sub = self.app.subscribe(self.cus.id, "team", date(2026, 4, 1))
        result = self.app.cancel(sub.id, date(2026, 4, 11))
        self.assertEqual(result.refund_cents, 2000)
        with self.assertRaises(Conflict):
            self.app.cancel(sub.id, date(2026, 4, 12))

    def test_seats(self):
        sub = self.app.subscribe(self.cus.id, "team", date(2026, 4, 1))
        change = self.app.add_seats(sub.id, 2, date(2026, 4, 16))
        self.assertEqual((change.charge_cents, change.quantity), (3000, 3))
        with self.assertRaises(ValidationError):
            self.app.add_seats(sub.id, 0, date(2026, 4, 16))

    def test_allowance(self):
        sub = self.app.subscribe(self.cus.id, "team", date(2026, 4, 11))
        self.assertEqual(self.app.allowance(sub.id, date(2026, 4, 20)), 200)
        self.assertEqual(self.app.allowance(sub.id, date(2026, 5, 2)), 300)


if __name__ == "__main__":
    unittest.main()

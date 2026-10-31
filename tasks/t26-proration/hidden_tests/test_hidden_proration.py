"""Hidden tests for t26-proration. Every rule is stated in the prompt or shown by the code; see AUDIT.md."""
import unittest
from datetime import date

from billkit import Billing, dunning, reports, trial
from billkit.usage import overage_cents


class Base(unittest.TestCase):
    def setUp(self):
        self.app = Billing()
        add = self.app.catalog.add
        add("m3", "Team", "month", 3000, included_units=300)
        add("m9", "Big", "month", 9000, included_units=900)
        add("y73", "Team yearly", "year", 73000, included_units=3600)
        add("y146", "Big yearly", "year", 146000, included_units=7200)
        self.cus = self.app.customers.create(name="Acme", email="a@acme.test").id

    def sub(self, plan, start, quantity=1, anchor_day=1):
        return self.app.subscribe(self.cus, plan, start, quantity=quantity, anchor_day=anchor_day)

    def first_line(self, sub):
        return self.app.invoices.for_subscription(sub.id)[0].lines[0]


class TestPlanChange(Base):
    def test_r1_february_28_days(self):
        s = self.sub("m3", date(2026, 2, 1))
        c = self.app.change_plan(s.id, "m9", date(2026, 2, 16))
        self.assertEqual((c.credit_cents, c.charge_cents), (1393, 4179))

    def test_r1_january_31_days(self):
        s = self.sub("m3", date(2026, 1, 1))
        c = self.app.change_plan(s.id, "m9", date(2026, 1, 11))
        self.assertEqual((c.credit_cents, c.charge_cents), (2032, 6097))

    def test_r1_february_29_days_in_a_leap_year(self):
        s = self.sub("m3", date(2028, 2, 1))
        c = self.app.change_plan(s.id, "m9", date(2028, 2, 15))
        self.assertEqual((c.credit_cents, c.charge_cents), (1552, 4655))

    def test_r1_period_that_does_not_start_on_the_first(self):
        s = self.sub("m3", date(2026, 1, 10), anchor_day=10)
        c = self.app.change_plan(s.id, "m9", date(2026, 2, 1))
        self.assertEqual((c.credit_cents, c.charge_cents), (871, 2613))

    def test_r1_seats_multiply_both_amounts(self):
        s = self.sub("m3", date(2026, 1, 1), quantity=3)
        c = self.app.change_plan(s.id, "m9", date(2026, 1, 11))
        self.assertEqual((c.credit_cents, c.charge_cents), (6097, 18290))

    def test_r1_yearly_365_days(self):
        s = self.sub("y73", date(2026, 3, 1))
        c = self.app.change_plan(s.id, "y146", date(2026, 9, 1))
        self.assertEqual((c.credit_cents, c.charge_cents), (36200, 72400))

    def test_r1_yearly_366_days(self):
        s = self.sub("y73", date(2027, 3, 1))
        c = self.app.change_plan(s.id, "y146", date(2027, 9, 1))
        self.assertEqual((c.credit_cents, c.charge_cents), (36301, 72601))

    def test_reg_whole_period_left_is_the_full_price(self):
        s = self.sub("m3", date(2026, 3, 1))
        c = self.app.change_plan(s.id, "m9", date(2026, 3, 1))
        self.assertEqual((c.credit_cents, c.charge_cents), (3000, 9000))

    def test_r1_invoice_lines_and_tax_follow_the_amounts(self):
        self.app.tax_rates.create(region="uk", label="VAT", bps=2000)
        uk = self.app.customers.create(name="Brit", email="b@b.test", region="uk").id
        s = self.app.subscribe(uk, "m3", date(2026, 2, 1))
        c = self.app.change_plan(s.id, "m9", date(2026, 2, 16))
        inv = self.app.invoices.get(c.invoice)
        self.assertEqual([line.amount_cents for line in inv.lines], [-1393, 4179])
        self.assertEqual((inv.subtotal_cents, inv.tax_cents), (2786, 557))
        self.assertEqual(inv.lines[1].period_end, date(2026, 3, 1))

    def test_reg_30_day_month_is_unchanged(self):
        s = self.sub("m3", date(2026, 4, 1))
        c = self.app.change_plan(s.id, "m9", date(2026, 4, 16))
        self.assertEqual((c.credit_cents, c.charge_cents, c.net_cents), (1500, 4500, 3000))


class TestFirstInvoice(Base):
    def test_r2_february_28_days(self):
        s = self.sub("m3", date(2026, 2, 10))
        self.assertEqual(self.first_line(s).amount_cents, 2035)

    def test_r2_january_31_days(self):
        s = self.sub("m3", date(2026, 1, 10))
        self.assertEqual(self.first_line(s).amount_cents, 2129)

    def test_r2_thirty_days_left_of_a_31_day_month_is_not_the_full_price(self):
        s = self.sub("m3", date(2026, 1, 2))
        self.assertEqual(self.first_line(s).amount_cents, 2903)

    def test_r2_february_29_days_in_a_leap_year(self):
        s = self.sub("m3", date(2028, 2, 10))
        self.assertEqual(self.first_line(s).amount_cents, 2068)

    def test_r2_cycle_anchored_on_the_15th(self):
        s = self.sub("m3", date(2026, 2, 20), anchor_day=15)
        line = self.first_line(s)
        self.assertEqual(line.amount_cents, 2464)
        self.assertEqual((line.period_start, line.period_end), (date(2026, 2, 20), date(2026, 3, 15)))

    def test_reg_start_on_the_anchor_day_pays_the_full_period(self):
        s = self.sub("m3", date(2026, 2, 1))
        line = self.first_line(s)
        self.assertEqual((line.amount_cents, line.kind), (3000, "subscription"))

    def test_reg_yearly_plans_pay_the_full_year(self):
        s = self.sub("y73", date(2028, 2, 10))
        line = self.first_line(s)
        self.assertEqual((line.amount_cents, line.period_end), (73000, date(2029, 2, 10)))


class TestCancellation(Base):
    def test_r3_february_28_days(self):
        s = self.sub("m3", date(2026, 2, 1))
        self.assertEqual(self.app.cancel(s.id, date(2026, 2, 16)).refund_cents, 1392)

    def test_r3_february_29_days_in_a_leap_year(self):
        s = self.sub("m3", date(2028, 2, 1))
        self.assertEqual(self.app.cancel(s.id, date(2028, 2, 15)).refund_cents, 1551)

    def test_r3_last_day_of_the_period(self):
        s = self.sub("m3", date(2026, 2, 1))
        self.assertEqual(self.app.cancel(s.id, date(2026, 2, 28)).refund_cents, 107)

    def test_r3_yearly_365_days(self):
        s = self.sub("y73", date(2026, 3, 1))
        self.assertEqual(self.app.cancel(s.id, date(2026, 9, 1)).refund_cents, 36200)

    def test_r3_yearly_366_days_rounds_down(self):
        s = self.sub("y73", date(2027, 3, 1))
        self.assertEqual(self.app.cancel(s.id, date(2027, 9, 1)).refund_cents, 36300)

    def test_r3_credit_note_carries_the_refund(self):
        s = self.sub("m3", date(2026, 2, 1))
        result = self.app.cancel(s.id, date(2026, 2, 16))
        note = self.app.invoices.get(result.credit_note)
        self.assertEqual((note.kind, note.subtotal_cents), ("credit_note", -1392))
        self.assertEqual(note.lines[0].period_end, date(2026, 3, 1))

    def test_reg_30_day_month_is_unchanged(self):
        s = self.sub("m3", date(2026, 4, 1))
        self.assertEqual(self.app.cancel(s.id, date(2026, 4, 11)).refund_cents, 2000)


class TestSeats(Base):
    def test_r4_february_28_days(self):
        s = self.sub("m3", date(2026, 2, 1))
        self.assertEqual(self.app.add_seats(s.id, 2, date(2026, 2, 16)).charge_cents, 2786)

    def test_r4_january_31_days(self):
        s = self.sub("m3", date(2026, 1, 1))
        self.assertEqual(self.app.add_seats(s.id, 2, date(2026, 1, 11)).charge_cents, 4065)

    def test_r4_february_29_days_in_a_leap_year(self):
        s = self.sub("m3", date(2028, 2, 1))
        self.assertEqual(self.app.add_seats(s.id, 2, date(2028, 2, 15)).charge_cents, 3103)

    def test_r4_yearly_365_and_366_days(self):
        a = self.sub("y73", date(2026, 3, 1))
        b = self.sub("y73", date(2027, 3, 1))
        self.assertEqual(self.app.add_seats(a.id, 1, date(2026, 9, 1)).charge_cents, 36200)
        self.assertEqual(self.app.add_seats(b.id, 1, date(2027, 9, 1)).charge_cents, 36301)

    def test_r4_quantity_and_invoice_line(self):
        s = self.sub("m3", date(2026, 2, 1))
        change = self.app.add_seats(s.id, 2, date(2026, 2, 16))
        self.assertEqual(change.quantity, 3)
        line = self.app.invoices.get(change.invoice).lines[0]
        self.assertEqual((line.amount_cents, line.period_end), (2786, date(2026, 3, 1)))

    def test_reg_30_day_month_and_no_refund_when_removing(self):
        s = self.sub("m3", date(2026, 4, 1), quantity=3)
        self.assertEqual(self.app.add_seats(s.id, 2, date(2026, 4, 16)).charge_cents, 3000)
        before = len(self.app.invoices)
        self.assertEqual(self.app.remove_seats(s.id, 1).charge_cents, 0)
        self.assertEqual(len(self.app.invoices), before)


class TestAllowance(Base):
    def test_r5_february_28_days(self):
        s = self.sub("m3", date(2026, 2, 10))
        self.assertEqual(self.app.allowance(s.id, date(2026, 2, 20)), 203)

    def test_r5_january_31_days(self):
        s = self.sub("m3", date(2026, 1, 10))
        self.assertEqual(self.app.allowance(s.id, date(2026, 1, 20)), 212)

    def test_r5_february_29_days_in_a_leap_year(self):
        s = self.sub("m3", date(2028, 2, 10))
        self.assertEqual(self.app.allowance(s.id, date(2028, 2, 20)), 206)

    def test_r5_overage_uses_the_partial_allowance(self):
        s = self.sub("m3", date(2026, 2, 10))
        self.app.usage.record(s.id, date(2026, 2, 12), 250)
        self.assertEqual(overage_cents(self.app, self.app.usage, s.id, date(2026, 2, 20), 5), 47 * 5)

    def test_reg_full_periods_get_the_full_allowance(self):
        s = self.sub("m3", date(2026, 2, 10))
        self.assertEqual(self.app.allowance(s.id, date(2026, 3, 2)), 300)
        y = self.sub("y73", date(2026, 2, 10))
        self.assertEqual(self.app.allowance(y.id, date(2026, 2, 12)), 3600)


class TestThirtyThatMustStay(Base):
    def test_reg_revenue_recognition_uses_the_days_of_the_line(self):
        s = self.sub("m3", date(2026, 2, 1))
        inv = self.app.invoices.for_subscription(s.id)[0]
        self.assertEqual(self.app.recognized(inv.id, 0, date(2026, 2, 15)), 1500)
        self.assertEqual(self.app.recognized(inv.id, 0, date(2026, 3, 1)), 3000)

    def test_reg_collections_buckets_and_suspension(self):
        self.assertEqual([dunning.overdue_bucket(d) for d in (0, 1, 30, 31, 60, 90, 91)],
                         ["current", "1-30", "1-30", "31-60", "31-60", "61-90", "90+"])

    def test_reg_aging_report_and_suspension(self):
        s = self.sub("m3", date(2026, 2, 1))
        inv = self.app.invoices.for_subscription(s.id)[0]
        self.assertFalse(dunning.should_suspend(inv, date(2026, 3, 15)))
        self.assertTrue(dunning.should_suspend(inv, date(2026, 3, 18)))
        self.assertEqual(reports.aging_report(self.app, date(2026, 3, 18)),
                         {"<=30": 0, "<=60": 3000, "<=90": 0, ">90": 0})

    def test_reg_trial_and_mrr(self):
        self.assertEqual(trial.trial_end(date(2026, 2, 1)), date(2026, 2, 15))
        self.sub("y73", date(2026, 2, 1))
        self.assertEqual(reports.mrr_cents(self.app), 6083)

    def test_reg_renewal_is_the_full_price(self):
        s = self.sub("m3", date(2026, 2, 10))
        from billkit import invoicing
        inv = invoicing.bill_renewal(self.app, s, date(2026, 3, 1))
        self.assertEqual(inv.subtotal_cents, 3000)


if __name__ == "__main__":
    unittest.main()

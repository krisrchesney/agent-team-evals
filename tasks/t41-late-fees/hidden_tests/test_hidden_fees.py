"""Hidden tests for t41-late-fees. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from billbook import Service
from billbook.clock import FixedClock
from billbook.errors import BillError, Conflict, InvalidRequest, NotFound

DUE = "2026-01-05"      # the same day as the fixed clock starts, so "day n" means n days after the due date


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.day = 0
        self.inv = self.invoice(100_000)
        self.svc.bus.log.clear()

    def invoice(self, amount, due=DUE, customer="cus-1"):
        return self.svc.call("invoice.create", customer=customer, amount=amount, due=due)["id"]

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def at(self, day):
        self.clock.advance(days=day - self.day)
        self.day = day

    def assess(self, **kw):
        return self.call("fee.assess", **kw)["data"]

    def get(self, inv=None):
        return self.call("invoice.retrieve", invoice=inv or self.inv)

    def fees(self, inv=None):
        return self.call("fee.list", invoice=inv or self.inv, limit=100)["data"]

    def pay(self, amount, inv=None):
        return self.call("invoice.pay", invoice=inv or self.inv, amount=amount)

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, BillError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestBasics(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"fee.assess", "fee.list"} <= ops)
        self.assertTrue({"invoice.pay", "payment.list"} <= ops)

    def test_fee_view(self):
        self.at(6)
        (fee,) = self.assess()
        self.assertEqual(fee["id"], "fee_0001")
        self.assertEqual((fee["invoice"], fee["amount"], fee["period"]), (self.inv, 2000, 1))
        self.assertEqual((fee["created_at"], fee["updated_at"], fee["version"]), ("2026-01-11T09:00:00Z",) * 2 + (1,))

    def test_invoice_view_has_late_fees(self):
        self.assertEqual(self.get()["late_fees"], 0)
        self.at(6)
        self.assess()
        v = self.get()
        self.assertEqual((v["late_fees"], v["amount"], v["paid"], v["balance"]), (2000, 100_000, 0, 102_000))

    def test_invoice_bumped_by_a_fee(self):
        self.at(6)
        self.assess()
        v = self.get()
        self.assertEqual((v["version"], v["updated_at"]), (2, "2026-01-11T09:00:00Z"))

    def test_assess_event(self):
        self.at(6)
        (fee,) = self.assess()
        (ev,) = self.svc.bus.log
        self.assertEqual(ev["type"], "fee.assessed")
        self.assertEqual(ev["data"]["fee"], fee)
        self.assertEqual(ev["data"]["invoice"], self.get())

    def test_nothing_to_assess(self):
        self.assertEqual(self.call("fee.assess"), {"data": []})
        self.assertEqual(self.svc.bus.log, [])

    def test_assess_twice_charges_once(self):
        self.at(6)
        self.assess()
        self.assertEqual(self.assess(), [])
        self.clock.advance(hours=5)
        self.assertEqual(self.assess(), [])
        self.assertEqual(len(self.fees()), 1)

    def test_assess_one_invoice(self):
        other = self.invoice(50_000)
        self.at(6)
        (fee,) = self.assess(invoice=other)
        self.assertEqual(fee["invoice"], other)
        self.assertEqual(self.get()["late_fees"], 0)

    def test_assess_unknown_invoice(self):
        self.assertError(NotFound, "invoice", "fee.assess", invoice="invoice_9999")
        self.assertError(InvalidRequest, "invoice", "fee.assess", invoice="  ")

    def test_fee_list(self):
        self.at(66)
        self.assess()
        out = self.call("fee.list", invoice=self.inv, limit=2)
        self.assertEqual(([f["period"] for f in out["data"]], out["has_more"]), ([1, 2], True))
        self.assertError(NotFound, "invoice", "fee.list", invoice="invoice_9999")
        self.assertError(InvalidRequest, "limit", "fee.list", invoice=self.inv, limit=0)

    def test_fee_ids_are_sequential_across_invoices(self):
        other = self.invoice(100_000)
        self.at(6)
        out = self.assess()
        self.assertEqual([f["id"] for f in out], ["fee_0001", "fee_0002"])
        self.assertEqual([f["invoice"] for f in out], [self.inv, other])


class TestGrace(Base):
    """answers.json: grace"""

    def test_nothing_up_to_day_5(self):
        for day in (0, 1, 5):
            self.at(day)
            self.assertEqual(self.assess(), [], day)

    def test_first_fee_on_day_6(self):
        self.at(5)
        self.assess()
        self.at(6)
        self.assertEqual(len(self.assess()), 1)

    def test_grace_counts_from_the_due_date(self):
        late = self.invoice(100_000, due="2026-01-03")     # due 2 days before the clock start
        self.at(3)                                          # 2026-01-08: day 5 for `late`, day 3 for the other
        self.assertEqual(self.assess(invoice=late), [])
        self.at(4)
        self.assertEqual(len(self.assess(invoice=late)), 1)
        self.assertEqual(self.assess(invoice=self.inv), [])

    def test_paid_invoices_get_no_fees(self):
        self.pay(100_000)
        self.at(100)
        self.assertEqual(self.assess(), [])

    def test_not_yet_due_invoice(self):
        future = self.invoice(100_000, due="2026-03-01")
        self.at(6)
        self.assertEqual(self.assess(invoice=future), [])


class TestAmount(Base):
    """answers.json: amount"""

    def test_two_percent(self):
        self.at(6)
        self.assertEqual(self.assess()[0]["amount"], 2000)

    def test_rounded_down(self):
        inv = self.invoice(12_399)          # 247.98 -> 247, below the minimum -> use a bigger one
        inv2 = self.invoice(123_399)        # 2467.98 -> 2467
        self.at(6)
        got = {f["invoice"]: f["amount"] for f in self.assess()}
        self.assertEqual(got[inv2], 2467)
        self.assertEqual(got[inv], 250)

    def test_minimum_250(self):
        small = self.invoice(5_000)
        self.at(6)
        got = {f["invoice"]: f["amount"] for f in self.assess()}
        self.assertEqual(got[small], 250)

    def test_exact_threshold_for_the_minimum(self):
        a = self.invoice(12_500)            # exactly 250
        b = self.invoice(12_549)            # 250.98 -> 250
        c = self.invoice(15_000)            # 300
        self.at(6)
        got = {f["invoice"]: f["amount"] for f in self.assess()}
        self.assertEqual((got[a], got[b], got[c]), (250, 250, 300))

    def test_based_on_what_is_still_unpaid(self):
        self.pay(40_000)
        self.at(6)
        self.assertEqual(self.assess()[0]["amount"], 1200)

    def test_minimum_even_when_little_is_left(self):
        self.pay(99_000)
        self.at(6)
        self.assertEqual(self.assess()[0]["amount"], 250)

    def test_minimum_after_a_payment_that_went_to_the_fee_first(self):
        self.at(6)
        self.assess()                       # 2000 fee
        self.pay(100_000)                   # fees first (2000), then 98000 of the invoice
        self.assertEqual(self.get()["status"], "open")
        self.at(36)
        self.assertEqual(self.assess()[0]["amount"], 250)   # 2000 left unpaid on the invoice amount -> 40 -> minimum


class TestRecurrence(Base):
    """answers.json: recurrence"""

    def test_second_fee_on_day_36(self):
        self.at(6)
        self.assess()
        self.at(35)
        self.assertEqual(self.assess(), [])
        self.at(36)
        (fee,) = self.assess()
        self.assertEqual((fee["period"], fee["amount"]), (2, 2000))

    def test_third_fee_on_day_66(self):
        self.at(65)
        self.assertEqual([f["period"] for f in self.assess()], [1, 2])
        self.at(66)
        self.assertEqual([f["period"] for f in self.assess()], [3])

    def test_fees_do_not_compound(self):
        self.at(6)
        self.assess()
        self.at(36)
        self.assess()
        self.at(66)
        self.assess()
        self.assertEqual([f["amount"] for f in self.fees()], [2000, 2000, 2000])

    def test_catch_up_charges_every_missed_period(self):
        self.at(70)
        out = self.assess()
        self.assertEqual([(f["period"], f["amount"]) for f in out], [(1, 2000), (2, 2000), (3, 2000)])
        self.assertEqual(self.get()["late_fees"], 6000)
        self.assertEqual(self.assess(), [])

    def test_catch_up_events_and_versions(self):
        self.at(36)
        self.assess()
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["fee.assessed"] * 2)
        self.assertEqual(self.get()["version"], 3)

    def test_catch_up_uses_the_current_balance(self):
        self.pay(50_000)
        self.at(40)
        self.assertEqual([f["amount"] for f in self.assess()], [1000, 1000])

    def test_stops_when_invoice_is_paid(self):
        self.at(6)
        self.assess()
        self.pay(102_000)
        self.assertEqual(self.get()["status"], "paid")
        self.at(100)
        self.assertEqual(self.assess(), [])

    def test_period_boundaries_per_invoice(self):
        other = self.invoice(100_000, due="2026-01-20")     # due 15 days after the clock start
        self.at(36)                                          # day 21 for `other`
        self.assertEqual([f["period"] for f in self.assess(invoice=other)], [1])
        self.assertEqual([f["period"] for f in self.assess(invoice=self.inv)], [1, 2])


class TestAllocation(Base):
    """answers.json: allocation"""

    def test_payment_covers_fees_first(self):
        self.at(6)
        self.assess()                                        # fee 2000
        self.pay(5_000)
        self.at(36)
        (fee,) = self.assess()
        # 2000 of the payment went to the fee, 3000 to the invoice: unpaid 97000 -> 1940
        self.assertEqual(fee["amount"], 1940)

    def test_balance_ignores_allocation(self):
        self.at(6)
        self.assess()
        v = self.pay(5_000)
        self.assertEqual((v["paid"], v["balance"], v["late_fees"]), (5_000, 97_000, 2_000))

    def test_earlier_payment_is_not_reallocated(self):
        self.pay(30_000)                                     # before any fee: all to the invoice
        self.at(6)
        self.assess()                                        # 2% of 70000 = 1400
        self.at(36)
        (fee,) = self.assess()
        self.assertEqual(fee["amount"], 1400)

    def test_payment_after_fee_spills_over(self):
        self.pay(30_000)
        self.at(6)
        self.assess()                                        # 1400
        self.pay(5_000)                                      # 1400 to fee, 3600 to invoice -> unpaid 66400
        self.at(36)
        (fee,) = self.assess()
        self.assertEqual(fee["amount"], 1328)

    def test_small_payment_stays_with_the_fee(self):
        self.at(6)
        self.assess()                                        # 2000
        self.pay(1_500)                                      # all to the fee
        self.at(36)
        self.assertEqual(self.assess()[0]["amount"], 2000)   # invoice amount untouched

    def test_second_payment_continues_with_the_fee(self):
        self.at(6)
        self.assess()
        self.pay(1_500)
        self.pay(1_500)                                      # 500 finishes the fee, 1000 to the invoice
        self.at(36)
        self.assertEqual(self.assess()[0]["amount"], 1980)

    def test_payment_may_pay_fees_in_full(self):
        self.at(6)
        self.assess()
        v = self.pay(102_000)
        self.assertEqual((v["balance"], v["status"]), (0, "paid"))

    def test_cannot_overpay_including_fees(self):
        self.at(6)
        self.assess()
        self.assertError(Conflict, "amount", "invoice.pay", invoice=self.inv, amount=102_001)

    def test_later_fees_are_paid_before_the_remaining_invoice(self):
        self.pay(20_000)                                     # invoice unpaid 80000
        self.at(6)
        self.assess()                                        # 1600
        self.at(36)
        self.assess()                                        # 1600
        self.pay(3_200)                                      # both fees, nothing for the invoice
        self.at(66)
        (fee,) = self.assess()
        self.assertEqual(fee["amount"], 1600)


class TestCap(Base):
    """answers.json: cap"""

    def test_total_never_exceeds_25_percent(self):
        inv = self.invoice(10_000)                           # cap 2500; every fee is the 250 minimum
        self.at(500)
        out = self.assess(invoice=inv)
        self.assertEqual([f["amount"] for f in out], [250] * 10)
        self.assertEqual(self.get(inv)["late_fees"], 2500)

    def test_last_fee_is_cut_to_fit(self):
        inv = self.invoice(10_010)                           # cap 2502
        self.at(500)
        out = self.assess(invoice=inv)
        self.assertEqual([f["amount"] for f in out], [250] * 10 + [2])
        self.assertEqual([f["period"] for f in out][-1], 11)

    def test_nothing_after_the_cap(self):
        inv = self.invoice(10_010)
        self.at(500)
        self.assess(invoice=inv)
        self.at(900)
        self.assertEqual(self.assess(invoice=inv), [])
        self.assertEqual(len(self.fees(inv)), 11)

    def test_cap_rounds_down(self):
        inv = self.invoice(10_003)                           # 25% = 2500.75 -> 2500
        self.at(500)
        self.assess(invoice=inv)
        self.assertEqual(self.get(inv)["late_fees"], 2500)

    def test_cap_counts_over_several_runs(self):
        inv = self.invoice(10_000)
        for day in (6, 36, 66, 96, 126, 156, 186, 216, 246, 276, 306):
            self.at(day)
            self.assess(invoice=inv)
        self.assertEqual(self.get(inv)["late_fees"], 2500)
        self.assertEqual(len(self.fees(inv)), 10)

    def test_cap_is_per_invoice(self):
        a, b = self.invoice(10_000), self.invoice(10_000)
        self.at(500)
        self.assess()
        self.assertEqual((self.get(a)["late_fees"], self.get(b)["late_fees"]), (2500, 2500))

    def test_paid_fees_still_count_towards_the_cap(self):
        inv = self.invoice(10_000)
        self.at(6)
        self.assess(invoice=inv)
        self.pay(250, inv)
        self.at(500)
        self.assess(invoice=inv)
        self.assertEqual(self.get(inv)["late_fees"], 2500)


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        v = self.get()
        self.assertEqual((v["balance"], v["status"], v["version"]), (100_000, "open", 1))
        out = self.pay(40_000)
        self.assertEqual((out["paid"], out["balance"], out["version"]), (40_000, 60_000, 2))
        self.assertEqual(len(self.call("payment.list", invoice=self.inv)["data"]), 1)
        self.assertEqual(len(self.call("invoice.list")["data"]), 1)


if __name__ == "__main__":
    unittest.main()

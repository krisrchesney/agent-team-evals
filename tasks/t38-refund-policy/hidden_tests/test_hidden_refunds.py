"""Hidden tests for t38-refund-policy. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from payledger import Service
from payledger.clock import FixedClock
from payledger.errors import Conflict, InvalidRequest, LedgerError, NotFound

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.charge = self.make(amount=2500, tax=200)
        self.svc.bus.log.clear()

    def make(self, amount=2500, tax=0, customer="cus-1", **kw):
        return self.svc.call("charge.create", customer=customer, amount=amount, tax=tax, **kw)["id"]

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def refund(self, amount=500, charge=None, **kw):
        return self.call("refund.create", charge=charge or self.charge, amount=amount, **kw)

    def get(self, charge=None):
        return self.call("charge.retrieve", charge=charge or self.charge)

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, LedgerError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestRegistration(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"refund.create", "refund.retrieve", "refund.list"} <= ops)
        self.assertTrue({"charge.create", "ledger.entries"} <= ops)


class TestCreate(Base):
    def test_r1_refund_view(self):
        r = self.refund(500, reason="  broken  ")
        self.assertEqual(r["id"], "refund_0001")
        self.assertEqual((r["charge"], r["amount"], r["reason"]), (self.charge, 500, "broken"))
        self.assertEqual((r["created_at"], r["updated_at"], r["version"]), (T0, T0, 1))
        self.assertEqual(self.refund(100)["id"], "refund_0002")

    def test_r1_reason_has_a_default(self):
        self.assertTrue(self.refund(500)["reason"])

    def test_r1_blank_reason_rejected(self):
        self.assertError(InvalidRequest, "reason", "refund.create", charge=self.charge, amount=5, reason="  ")

    def test_r1_event(self):
        r = self.refund(500)
        (ev,) = self.svc.bus.log
        self.assertEqual(ev["type"], "refund.created")
        self.assertEqual(ev["data"]["refund"], r)
        self.assertEqual(ev["data"]["entry"], self.call("ledger.entries", charge=self.charge)["data"][-1])

    def test_r1_unknown_charge(self):
        self.assertError(NotFound, "charge", "refund.create", charge="charge_9999", amount=1)

    def test_r1_charge_checked_before_amount(self):
        self.assertError(NotFound, "charge", "refund.create", charge="charge_9999", amount=0)

    def test_r1_bad_amounts(self):
        for a in (0, -1, True, "5", 2.0, 10_000_001, None):
            with self.subTest(a=a):
                self.assertError(InvalidRequest, "amount", "refund.create", charge=self.charge, amount=a)

    def test_r1_missing_charge(self):
        self.assertError(InvalidRequest, "charge", "refund.create", amount=5)

    def test_r1_failures_change_nothing(self):
        before = self.get()
        for params in ({"charge": "charge_9999", "amount": 1}, {"charge": self.charge, "amount": 0},
                       {"charge": self.charge, "amount": 2501}):
            with self.assertRaises(LedgerError):
                self.call("refund.create", **params)
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.get(), before)
        self.assertEqual(len(self.call("ledger.entries", charge=self.charge)["data"]), 1)
        self.assertEqual(self.refund(1)["id"], "refund_0001")


class TestChargeAndLedger(Base):
    def test_r2_charge_fields(self):
        self.clock.advance(minutes=5)
        self.refund(500)
        c = self.get()
        self.assertEqual((c["refunded"], c["status"], c["version"]), (500, "partially_refunded", 2))
        self.assertEqual(c["updated_at"], "2026-01-05T09:05:00Z")
        self.assertEqual(c["amount"], 2500)

    def test_r2_fully_refunded(self):
        self.refund(1000)
        self.refund(1500)
        c = self.get()
        self.assertEqual((c["refunded"], c["status"], c["version"]), (2500, "refunded", 3))

    def test_r2_ledger_entry(self):
        self.refund(500, reason="late")
        rows = self.call("ledger.entries", charge=self.charge)["data"]
        self.assertEqual([(r["kind"], r["amount"], r["ref"]) for r in rows], [("charge", 2500, "charge"), ("refund", -500, "late")])
        self.assertEqual(rows[1]["id"], "entry_0002")

    def test_r2_ledger_ref_is_the_reason(self):
        r = self.refund(500)
        self.assertEqual(self.call("ledger.entries", charge=self.charge)["data"][-1]["ref"], r["reason"])

    def test_r2_other_charges_untouched(self):
        other = self.make(amount=900)
        self.refund(500)
        self.assertEqual(self.get(other)["refunded"], 0)
        self.assertEqual(len(self.call("ledger.entries", charge=other)["data"]), 1)


class TestRetrieveAndList(Base):
    def test_r3_retrieve(self):
        r = self.refund(500)
        self.assertEqual(self.call("refund.retrieve", refund=r["id"]), r)

    def test_r3_retrieve_unknown_and_missing(self):
        self.assertError(NotFound, "refund", "refund.retrieve", refund="refund_9999")
        self.assertError(InvalidRequest, "refund", "refund.retrieve")

    def test_r3_reads_emit_nothing(self):
        r = self.refund(500)
        self.svc.bus.log.clear()
        self.call("refund.retrieve", refund=r["id"])
        self.call("refund.list", charge=self.charge)
        self.assertEqual(self.svc.bus.log, [])

    def test_r3_list_for_one_charge_in_order(self):
        other = self.make(amount=900)
        a = self.refund(100)
        self.refund(100, charge=other)
        self.clock.advance(minutes=1)
        b = self.refund(200)
        out = self.call("refund.list", charge=self.charge)
        self.assertEqual(out, {"data": [a, b], "has_more": False})

    def test_r3_list_limit(self):
        for _ in range(3):
            self.refund(10)
        out = self.call("refund.list", charge=self.charge, limit=2)
        self.assertEqual((len(out["data"]), out["has_more"]), (2, True))
        self.assertError(InvalidRequest, "limit", "refund.list", charge=self.charge, limit=0)

    def test_r3_list_unknown_charge(self):
        self.assertError(NotFound, "charge", "refund.list", charge="charge_9999")


class TestWindow(Base):
    """answers.json: window"""

    def test_window_inclusive_at_30_days(self):
        self.clock.advance(days=30)
        self.assertEqual(self.refund(500)["amount"], 500)

    def test_window_closed_one_second_later(self):
        self.clock.advance(days=30, seconds=1)
        self.assertError(Conflict, "charge", "refund.create", charge=self.charge, amount=500)
        self.assertEqual(self.get()["refunded"], 0)
        self.assertEqual(self.svc.bus.log, [])

    def test_window_counts_from_this_charge(self):
        self.clock.advance(days=20)
        young = self.make(amount=1000)
        self.clock.advance(days=15)
        self.assertEqual(self.refund(100, charge=young)["charge"], young)
        self.assertError(Conflict, "charge", "refund.create", charge=self.charge, amount=100)

    def test_window_applies_to_later_refunds_too(self):
        self.refund(100)
        self.clock.advance(days=31)
        self.assertError(Conflict, "charge", "refund.create", charge=self.charge, amount=100)

    def test_window_is_a_conflict_not_invalid(self):
        self.clock.advance(days=40)
        with self.assertRaises(Conflict) as ctx:
            self.refund(1)
        self.assertNotIsInstance(ctx.exception, InvalidRequest)


class TestOverRefund(Base):
    """answers.json: over_refund"""

    def test_cannot_exceed_charge(self):
        self.assertError(Conflict, "amount", "refund.create", charge=self.charge, amount=2501)

    def test_exactly_the_charge_is_fine(self):
        self.assertEqual(self.refund(2500, approved_by="sam")["amount"], 2500)
        self.assertEqual(self.get()["status"], "refunded")

    def test_cumulative_total_counts(self):
        self.refund(2000, approved_by="sam")
        self.assertError(Conflict, "amount", "refund.create", charge=self.charge, amount=501)

    def test_not_capped_down(self):
        self.refund(2000, approved_by="sam")
        with self.assertRaises(Conflict):
            self.refund(600)
        self.assertEqual(self.get()["refunded"], 2000)
        self.assertEqual(len(self.call("refund.list", charge=self.charge)["data"]), 1)
        self.assertEqual(self.refund(500)["amount"], 500)

    def test_nothing_left_after_full_refund(self):
        self.refund(2500, approved_by="sam")
        self.assertError(Conflict, "amount", "refund.create", charge=self.charge, amount=1)


class TestTax(Base):
    """answers.json: tax"""

    def test_proportional_share(self):
        self.assertEqual(self.refund(500)["tax"], 40)       # 200 * 500 / 2500

    def test_half_up(self):
        c = self.make(amount=1000, tax=5)
        self.assertEqual(self.refund(100, charge=c)["tax"], 1)    # 0.5 -> 1
        c2 = self.make(amount=1000, tax=7)
        self.assertEqual(self.refund(500, charge=c2)["tax"], 4)   # 3.5 -> 4

    def test_rounds_down_below_half(self):
        c = self.make(amount=1000, tax=3)
        self.assertEqual(self.refund(100, charge=c)["tax"], 0)    # 0.3 -> 0

    def test_no_tax_charge(self):
        c = self.make(amount=1000)
        self.assertEqual(self.refund(400, charge=c)["tax"], 0)

    def test_final_refund_takes_the_remainder(self):
        c = self.make(amount=300, tax=100)
        taxes = [self.refund(100, charge=c)["tax"] for _ in range(3)]
        self.assertEqual(taxes, [33, 33, 34])

    def test_never_more_than_unrefunded_tax(self):
        c = self.make(amount=5, tax=3)
        taxes = [self.refund(1, charge=c)["tax"] for _ in range(5)]
        self.assertEqual(taxes, [1, 1, 1, 0, 0])

    def test_single_full_refund_takes_all_tax(self):
        self.assertEqual(self.refund(2500, approved_by="sam")["tax"], 200)

    def test_totals_always_match(self):
        c = self.make(amount=997, tax=83)
        total = 0
        for a in (101, 333, 7, 556):
            total += self.refund(a, charge=c)["tax"]
        self.assertEqual(total, 83)
        self.assertEqual(self.get(c)["status"], "refunded")


class TestApproval(Base):
    """answers.json: approval"""

    def setUp(self):
        super().setUp()
        self.big = self.make(amount=50_000)
        self.svc.bus.log.clear()

    def test_over_threshold_needs_approver(self):
        self.assertError(InvalidRequest, "approved_by", "refund.create", charge=self.big, amount=10_001)
        self.assertError(InvalidRequest, "approved_by", "refund.create", charge=self.big, amount=20_000, approved_by="  ")

    def test_exactly_threshold_needs_none(self):
        r = self.refund(10_000, charge=self.big)
        self.assertIsNone(r["approved_by"])

    def test_approver_is_stored_stripped(self):
        r = self.refund(10_001, charge=self.big, approved_by="  dana ")
        self.assertEqual(r["approved_by"], "dana")
        self.assertEqual(self.call("refund.retrieve", refund=r["id"])["approved_by"], "dana")

    def test_small_refund_may_carry_one(self):
        self.assertEqual(self.refund(5, charge=self.big, approved_by="dana")["approved_by"], "dana")

    def test_null_when_not_given(self):
        self.assertIsNone(self.refund(5, charge=self.big)["approved_by"])

    def test_missing_approver_changes_nothing(self):
        with self.assertRaises(InvalidRequest):
            self.refund(10_001, charge=self.big)
        self.assertEqual(self.get(self.big)["refunded"], 0)
        self.assertEqual(self.svc.bus.log, [])

    def test_threshold_is_per_refund_not_cumulative(self):
        self.refund(8000, charge=self.big)
        self.assertEqual(self.refund(8000, charge=self.big)["amount"], 8000)


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        c = self.get()
        self.assertEqual((c["refunded"], c["status"], c["version"]), (0, "succeeded", 1))
        rows = self.call("charge.list", customer="cus-1")["data"]
        self.assertEqual([r["id"] for r in rows], [self.charge])
        self.assertEqual(len(self.call("ledger.entries", charge=self.charge)["data"]), 1)


if __name__ == "__main__":
    unittest.main()

"""Hidden tests for t43-vouchers. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from shopcredit import Service
from shopcredit.clock import FixedClock
from shopcredit.errors import Conflict, CreditError, InvalidRequest, NotFound

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.kim = self.svc.call("customer.create", name="Kim")["id"]
        self.order = self.new_order(4500)
        self.svc.bus.log.clear()

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def new_order(self, total=4500):
        return self.call("order.create", customer=self.kim, total=total)["id"]

    def issue(self, amount=2500):
        return self.call("voucher.issue", amount=amount)

    def redeem(self, voucher, order=None):
        return self.call("voucher.redeem", voucher=voucher, order=order or self.order)

    def get_order(self, order=None):
        return self.call("order.retrieve", order=order or self.order)

    def get_voucher(self, voucher):
        return self.call("voucher.retrieve", voucher=voucher)

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, CreditError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestIssue(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"voucher.issue", "voucher.redeem", "voucher.void", "voucher.retrieve"} <= ops)
        self.assertTrue({"order.create", "order.pay", "customer.create"} <= ops)

    def test_voucher_view(self):
        v = self.issue(2500)
        self.assertEqual(v["id"], "voucher_0001")
        self.assertEqual((v["amount"], v["balance"], v["status"]), (2500, 2500, "active"))
        self.assertEqual((v["created_at"], v["updated_at"], v["version"]), (T0, T0, 1))
        self.assertEqual(self.issue(100)["id"], "voucher_0002")

    def test_issue_event(self):
        v = self.issue()
        self.assertEqual(self.svc.bus.log, [{"type": "voucher.issued", "data": {"voucher": v}}])

    def test_bad_amounts(self):
        for amount in (0, -5, 12.5, "10", True, None):
            with self.subTest(amount=amount):
                self.assertError(InvalidRequest, "amount", "voucher.issue", amount=amount)
        self.assertError(InvalidRequest, "amount", "voucher.issue")

    def test_failures_change_nothing(self):
        with self.assertRaises(CreditError):
            self.call("voucher.issue", amount=0)
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.issue()["id"], "voucher_0001")

    def test_retrieve(self):
        v = self.issue()
        self.svc.bus.log.clear()
        self.assertEqual(self.get_voucher(v["id"]), v)
        self.assertEqual(self.svc.bus.log, [])
        self.assertError(NotFound, "voucher", "voucher.retrieve", voucher="voucher_9999")
        self.assertError(InvalidRequest, "voucher", "voucher.retrieve")

    def test_orders_show_credited(self):
        o = self.get_order()
        self.assertEqual((o["credited"], o["total"], o["status"]), (0, 4500, "open"))


class TestRedeemBasics(Base):
    def test_redeem_event(self):
        v = self.issue(4500)
        self.svc.bus.log.clear()
        out = self.redeem(v["id"])
        self.assertEqual(self.svc.bus.log, [{"type": "voucher.redeemed", "data": {"voucher": out}}])
        self.assertEqual((out["version"], out["updated_at"]), (2, T0))

    def test_unknown_voucher_and_order(self):
        v = self.issue()
        self.assertError(NotFound, "voucher", "voucher.redeem", voucher="voucher_9999", order=self.order)
        self.assertError(NotFound, "order", "voucher.redeem", voucher=v["id"], order="order_9999")

    def test_missing_arguments(self):
        v = self.issue()
        self.assertError(InvalidRequest, "voucher", "voucher.redeem", order=self.order)
        self.assertError(InvalidRequest, "order", "voucher.redeem", voucher=v["id"])

    def test_failures_change_nothing(self):
        v = self.issue()
        self.svc.bus.log.clear()
        with self.assertRaises(NotFound):
            self.call("voucher.redeem", voucher=v["id"], order="order_9999")
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.get_voucher(v["id"])["balance"], 2500)

    def test_order_changes_are_silent_but_stamped(self):
        self.clock.advance(hours=2)
        v = self.issue(2000)
        self.svc.bus.log.clear()
        self.redeem(v["id"])
        self.assertEqual(self.get_order()["version"], 2)
        self.assertEqual(self.get_order()["updated_at"], "2026-01-05T11:00:00Z")
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["voucher.redeemed"])


class TestAmounts(Base):
    """answers.json: remainder"""

    def test_voucher_smaller_than_the_order(self):
        v = self.issue(2500)
        out = self.redeem(v["id"])
        self.assertEqual((out["balance"], out["status"]), (0, "used"))
        o = self.get_order()
        self.assertEqual((o["credited"], o["status"]), (2500, "open"))

    def test_voucher_bigger_than_the_order_keeps_the_rest(self):
        v = self.issue(10000)
        out = self.redeem(v["id"])
        self.assertEqual((out["amount"], out["balance"], out["status"]), (10000, 5500, "active"))
        self.assertEqual(self.get_order()["credited"], 4500)

    def test_exact_cover_uses_the_voucher_up(self):
        out = self.redeem(self.issue(4500)["id"])
        self.assertEqual((out["balance"], out["status"]), (0, "used"))
        self.assertEqual(self.get_order()["credited"], 4500)

    def test_the_rest_can_be_used_on_other_orders(self):
        v = self.issue(10000)["id"]
        self.redeem(v)
        second = self.new_order(3000)
        out = self.redeem(v, second)
        self.assertEqual((out["balance"], out["status"]), (2500, "active"))
        self.assertEqual(self.get_order(second)["credited"], 3000)
        third = self.new_order(9000)
        out = self.redeem(v, third)
        self.assertEqual((out["balance"], out["status"]), (0, "used"))
        self.assertEqual(self.get_order(third)["credited"], 2500)

    def test_a_used_voucher_cannot_be_redeemed_again(self):
        v = self.issue(2500)["id"]
        self.redeem(v)
        other = self.new_order(1000)
        self.assertError(Conflict, "voucher", "voucher.redeem", voucher=v, order=other)
        self.assertEqual(self.get_order(other)["credited"], 0)


class TestValidity(Base):
    """answers.json: validity"""

    def test_expires_after_365_days(self):
        v = self.issue()
        self.assertEqual(v["expires_at"], "2027-01-05T09:00:00Z")
        self.clock.advance(days=10)
        self.assertEqual(self.issue()["expires_at"], "2027-01-15T09:00:00Z")

    def test_still_active_a_second_before(self):
        v = self.issue()["id"]
        self.clock.advance(days=364, hours=23, minutes=59, seconds=59)
        self.assertEqual(self.get_voucher(v)["status"], "active")
        self.assertEqual(self.redeem(v)["status"], "used")

    def test_expired_at_the_moment_itself(self):
        v = self.issue()["id"]
        self.clock.advance(days=365)
        self.assertEqual(self.get_voucher(v)["status"], "expired")

    def test_expired_cannot_be_redeemed(self):
        v = self.issue()["id"]
        self.clock.advance(days=365)
        self.assertError(Conflict, "voucher", "voucher.redeem", voucher=v, order=self.order)
        self.assertEqual(self.get_order()["credited"], 0)

    def test_a_partly_used_voucher_expires_with_its_balance(self):
        v = self.issue(10000)["id"]
        self.redeem(v)
        self.clock.advance(days=366)
        out = self.get_voucher(v)
        self.assertEqual((out["status"], out["balance"]), ("expired", 5500))

    def test_used_and_void_vouchers_do_not_turn_expired(self):
        used = self.issue(4500)["id"]
        self.redeem(used)
        gone = self.issue(100)["id"]
        self.call("voucher.void", voucher=gone)
        self.clock.advance(days=400)
        self.assertEqual((self.get_voucher(used)["status"], self.get_voucher(gone)["status"]), ("used", "void"))

    def test_expiry_emits_no_event(self):
        v = self.issue()["id"]
        self.svc.bus.log.clear()
        self.clock.advance(days=400)
        self.get_voucher(v)
        self.assertEqual(self.svc.bus.log, [])


class TestOnePerOrder(Base):
    """answers.json: one_per_order"""

    def test_a_second_voucher_is_refused(self):
        a = self.issue(2000)["id"]
        b = self.issue(1000)["id"]
        self.redeem(a)
        self.svc.bus.log.clear()
        self.assertError(Conflict, "order", "voucher.redeem", voucher=b, order=self.order)
        self.assertEqual(self.svc.bus.log, [])

    def test_the_refusal_changes_nothing(self):
        a = self.issue(2000)["id"]
        b = self.issue(1000)["id"]
        self.redeem(a)
        with self.assertRaises(Conflict):
            self.redeem(b)
        self.assertEqual(self.get_voucher(b)["balance"], 1000)
        self.assertEqual(self.get_voucher(b)["version"], 1)
        self.assertEqual(self.get_order()["credited"], 2000)

    def test_a_partly_used_first_voucher_still_blocks(self):
        a = self.issue(10000)["id"]
        small = self.new_order(1000)
        self.redeem(a, small)
        other = self.issue(500)["id"]
        self.assertError(Conflict, "order", "voucher.redeem", voucher=other, order=small)

    def test_other_orders_take_their_own_voucher(self):
        a = self.issue(2000)["id"]
        b = self.issue(1000)["id"]
        second = self.new_order(5000)
        self.redeem(a)
        self.assertEqual(self.redeem(b, second)["status"], "used")
        self.assertEqual(self.get_order(second)["credited"], 1000)


class TestVoid(Base):
    """answers.json: void"""

    def test_void_an_untouched_voucher(self):
        v = self.issue(2500)["id"]
        self.svc.bus.log.clear()
        out = self.call("voucher.void", voucher=v)
        self.assertEqual((out["status"], out["balance"], out["amount"], out["version"]), ("void", 0, 2500, 2))
        self.assertEqual(self.svc.bus.log, [{"type": "voucher.voided", "data": {"voucher": out}}])

    def test_a_voided_voucher_cannot_be_redeemed(self):
        v = self.issue(2500)["id"]
        self.call("voucher.void", voucher=v)
        self.assertError(Conflict, "voucher", "voucher.redeem", voucher=v, order=self.order)

    def test_a_partly_used_voucher_cannot_be_voided(self):
        v = self.issue(10000)["id"]
        self.redeem(v)
        self.assertError(Conflict, "voucher", "voucher.void", voucher=v)
        self.assertEqual(self.get_voucher(v)["balance"], 5500)

    def test_a_used_voucher_cannot_be_voided(self):
        v = self.issue(2500)["id"]
        self.redeem(v)
        self.assertError(Conflict, "voucher", "voucher.void", voucher=v)

    def test_void_twice_is_a_conflict(self):
        v = self.issue()["id"]
        self.call("voucher.void", voucher=v)
        self.assertError(Conflict, "voucher", "voucher.void", voucher=v)

    def test_an_expired_voucher_cannot_be_voided(self):
        v = self.issue()["id"]
        self.clock.advance(days=365)
        self.assertError(Conflict, "voucher", "voucher.void", voucher=v)
        self.assertEqual(self.get_voucher(v)["status"], "expired")

    def test_refused_void_changes_nothing(self):
        v = self.issue(2500)["id"]
        self.redeem(v)
        self.svc.bus.log.clear()
        with self.assertRaises(Conflict):
            self.call("voucher.void", voucher=v)
        self.assertEqual(self.svc.bus.log, [])
        self.assertError(NotFound, "voucher", "voucher.void", voucher="voucher_9999")
        self.assertError(InvalidRequest, "voucher", "voucher.void")


class TestSettle(Base):
    """answers.json: settle"""

    def test_a_fully_covered_order_is_paid_at_once(self):
        self.redeem(self.issue(4500)["id"])
        o = self.get_order()
        self.assertEqual((o["status"], o["credited"]), ("paid", 4500))

    def test_a_bigger_voucher_also_settles(self):
        self.redeem(self.issue(10000)["id"])
        self.assertEqual(self.get_order()["status"], "paid")

    def test_settling_emits_no_order_event(self):
        v = self.issue(4500)
        self.svc.bus.log.clear()
        self.redeem(v["id"])
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["voucher.redeemed"])

    def test_a_settled_order_cannot_be_paid_again(self):
        self.redeem(self.issue(4500)["id"])
        self.assertError(Conflict, "order", "order.pay", order=self.order)

    def test_a_partly_covered_order_stays_open_and_can_be_paid(self):
        self.redeem(self.issue(1000)["id"])
        self.assertEqual(self.get_order()["status"], "open")
        self.assertEqual(self.call("order.pay", order=self.order)["status"], "paid")


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        o = self.get_order()
        self.assertEqual((o["id"], o["customer"], o["total"], o["status"], o["version"]),
                         ("order_0001", self.kim, 4500, "open", 1))
        paid = self.call("order.pay", order=self.order)
        self.assertEqual((paid["status"], paid["version"]), ("paid", 2))
        self.assertError(Conflict, "order", "order.pay", order=self.order)
        self.assertError(InvalidRequest, "total", "order.create", customer=self.kim, total=0)


if __name__ == "__main__":
    unittest.main()

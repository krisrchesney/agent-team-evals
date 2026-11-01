"""Hidden tests for t48-order-points. Every rule is shown by the starting code; see AUDIT.md."""
import unittest

from orderflow import Service
from orderflow.clock import FixedClock
from orderflow.errors import Conflict, FlowError, InvalidRequest


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def place(self, total=2500, customer="ada"):
        return self.call("order.place", customer=customer, total=total)["id"]

    def shipped(self, total=2500, customer="ada"):
        oid = self.place(total, customer)
        for action in ("pay", "pack", "ship"):
            self.call(f"order.{action}", order=oid)
        return oid

    def deliver(self, total=2500, customer="ada"):
        oid = self.shipped(total, customer)
        self.svc.bus.log.clear()
        self.call("order.deliver", order=oid)
        return oid

    def balance(self, customer="ada"):
        return self.call("customer.points", customer=customer)["balance"]

    def types(self):
        return [e["type"] for e in self.svc.bus.log]

    def awards(self):
        return [e["data"]["points"] for e in self.svc.bus.log if e["type"] == "points.awarded"]


class TestAwards(Base):
    def test_operation_is_registered(self):
        self.assertIn("customer.points", self.svc.operations())

    def test_an_unknown_customer_has_nothing(self):
        self.assertEqual(self.call("customer.points", customer="nobody"), {"customer": "nobody", "balance": 0})

    def test_one_point_per_full_ten(self):
        oid = self.deliver(total=2500)
        self.assertEqual(self.balance(), 2)
        self.assertEqual(self.awards(), [{"order": oid, "customer": "ada", "points": 2, "balance": 2}])

    def test_rounding_goes_down(self):
        self.deliver(total=999)
        self.assertEqual(self.balance(), 0)
        self.deliver(total=1000)
        self.assertEqual(self.balance(), 1)
        self.deliver(total=1999)
        self.assertEqual(self.balance(), 2)

    def test_nothing_to_credit_means_no_event(self):
        self.deliver(total=999)
        self.assertEqual(self.types(), ["order.delivered", "notice.queued"])

    def test_the_event_comes_between_the_order_and_the_notice(self):
        self.deliver(total=5000)
        self.assertEqual(self.types(), ["order.delivered", "points.awarded", "notice.queued"])

    def test_the_event_carries_the_new_balance(self):
        self.deliver(total=3000)
        self.deliver(total=4000)
        self.assertEqual([(a["points"], a["balance"]) for a in self.awards()], [(4, 7)])
        self.assertEqual(self.balance(), 7)

    def test_only_delivery_awards_points(self):
        oid = self.place(total=50_000)
        for action in ("pay", "pack", "ship"):
            self.call(f"order.{action}", order=oid)
        self.assertEqual(self.balance(), 0)
        self.assertNotIn("points.awarded", self.types())

    def test_a_cancelled_order_earns_nothing(self):
        oid = self.place(total=50_000)
        self.call("order.pay", order=oid)
        self.svc.bus.log.clear()
        self.call("order.cancel", order=oid)
        self.assertEqual(self.types(), ["order.cancelled", "notice.queued"])
        self.assertEqual(self.balance(), 0)

    def test_the_order_is_only_bumped_by_its_move(self):
        oid = self.deliver(total=5000)
        order = self.call("order.retrieve", order=oid)
        self.assertEqual((order["status"], order["version"]), ("delivered", 5))

    def test_a_failed_delivery_awards_nothing(self):
        oid = self.place(total=50_000)
        with self.assertRaises(Conflict):
            self.call("order.deliver", order=oid)
        self.assertEqual(self.balance(), 0)
        self.assertNotIn("points.awarded", self.types())

    def test_delivering_twice_awards_once(self):
        oid = self.deliver(total=5000)
        with self.assertRaises(Conflict):
            self.call("order.deliver", order=oid)
        self.assertEqual(self.balance(), 5)

    def test_customer_is_read_like_other_strings(self):
        self.deliver(total=5000)
        self.assertEqual(self.call("customer.points", customer="  ada ")["customer"], "ada")
        for params in ({}, {"customer": ""}, {"customer": 5}):
            with self.assertRaises(InvalidRequest) as ctx:
                self.call("customer.points", **params)
            self.assertIsInstance(ctx.exception, FlowError)
            self.assertEqual(ctx.exception.param, "customer")


class TestDailyCap(Base):
    def test_the_cap_cuts_the_award(self):
        self.deliver(total=40_000)
        self.deliver(total=40_000)
        self.assertEqual(self.awards(), [{"order": "order_0002", "customer": "ada", "points": 10, "balance": 50}])
        self.assertEqual(self.balance(), 50)

    def test_a_full_day_earns_no_event(self):
        self.deliver(total=50_000)
        self.assertEqual(self.balance(), 50)
        self.deliver(total=50_000)
        self.assertEqual(self.types(), ["order.delivered", "notice.queued"])
        self.assertEqual(self.balance(), 50)

    def test_the_cap_is_per_customer(self):
        self.deliver(total=50_000, customer="ada")
        self.deliver(total=30_000, customer="bob")
        self.assertEqual((self.balance("ada"), self.balance("bob")), (50, 30))

    def test_the_cap_starts_again_the_next_day(self):
        self.deliver(total=50_000)
        self.clock.advance(hours=15)
        self.deliver(total=20_000)
        self.assertEqual([a["points"] for a in self.awards()], [20])
        self.assertEqual(self.balance(), 70)

    def test_balances_are_not_a_daily_thing(self):
        self.deliver(total=30_000)
        self.clock.advance(days=3)
        self.assertEqual(self.balance(), 30)
        self.deliver(total=10_000)
        self.assertEqual(self.balance(), 40)

    def test_the_day_that_counts_is_the_day_of_delivery(self):
        late = self.shipped(total=50_000)
        self.deliver(total=50_000)
        self.clock.advance(days=1)
        self.svc.bus.log.clear()
        self.call("order.deliver", order=late)
        self.assertEqual([a["points"] for a in self.awards()], [50])
        self.assertEqual(self.balance(), 100)

    def test_a_day_boundary_in_the_middle_of_the_evening(self):
        self.clock.advance(hours=14, minutes=59)   # 23:59
        self.deliver(total=50_000)
        self.clock.advance(minutes=2)              # 00:01 next day
        self.deliver(total=50_000)
        self.assertEqual(self.balance(), 100)

    def test_the_cap_stays_in_force_for_the_rest_of_the_day(self):
        self.deliver(total=50_000)
        self.clock.advance(hours=10)
        self.deliver(total=50_000)
        self.assertEqual(self.balance(), 50)
        self.assertEqual(self.awards(), [])


class TestExisting(Base):
    def test_the_limits_still_reset_each_day(self):
        for n in range(5):
            self.call("order.pay", order=self.place(customer=f"c{n}"))
        with self.assertRaises(Conflict):
            self.call("order.pay", order=self.place())
        self.clock.advance(days=1)
        self.call("order.pay", order="order_0006")

    def test_pay_events_are_unchanged(self):
        oid = self.place()
        self.svc.bus.log.clear()
        self.call("order.pay", order=oid)
        self.assertEqual(self.types(), ["order.paid", "notice.queued"])


if __name__ == "__main__":
    unittest.main()

import unittest

from orderflow import Service
from orderflow.clock import FixedClock
from orderflow.errors import Conflict, InvalidRequest, NotFound


class OrderTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)

    def order(self, total=2500, customer="ada"):
        return self.svc.call("order.place", customer=customer, total=total)["id"]

    def test_the_happy_path(self):
        oid = self.order()
        for action, status in (("pay", "paid"), ("pack", "packed"), ("ship", "shipped"), ("deliver", "delivered")):
            self.assertEqual(self.svc.call(f"order.{action}", order=oid)["status"], status)
        self.assertEqual(self.svc.call("order.retrieve", order=oid)["version"], 5)

    def test_events_come_in_a_set_order(self):
        oid = self.order()
        self.svc.call("order.pay", order=oid)
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["order.placed", "order.paid", "notice.queued"])

    def test_conflicts_and_errors(self):
        oid = self.order()
        with self.assertRaises(Conflict):
            self.svc.call("order.ship", order=oid)
        with self.assertRaises(NotFound):
            self.svc.call("order.pay", order="order_9999")
        with self.assertRaises(InvalidRequest):
            self.svc.call("order.place", customer="ada", total=0)

    def test_the_daily_limit_resets_each_day(self):
        for n in range(5):
            self.svc.call("order.pay", order=self.order(customer=f"c{n}"))
        with self.assertRaises(Conflict):
            self.svc.call("order.pay", order=self.order())
        self.assertIn("limit.reached", [e["type"] for e in self.svc.bus.log])
        self.clock.advance(days=1)
        self.svc.call("order.pay", order="order_0006")

    def test_the_daily_spend_limit(self):
        self.svc.call("order.pay", order=self.order(total=150_000))
        with self.assertRaises(Conflict):
            self.svc.call("order.pay", order=self.order(total=60_000))
        self.svc.call("order.pay", order=self.order(total=60_000, customer="bob"))
        self.clock.advance(days=1)
        self.svc.call("order.pay", order="order_0002")


if __name__ == "__main__":
    unittest.main()

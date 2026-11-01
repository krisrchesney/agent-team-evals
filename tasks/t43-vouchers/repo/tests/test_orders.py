import unittest

from shopcredit import Service
from shopcredit.clock import FixedClock
from shopcredit.errors import Conflict, InvalidRequest, NotFound


class OrdersTest(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.kim = self.svc.call("customer.create", name="Kim")["id"]

    def order(self, total=4500):
        return self.svc.call("order.create", customer=self.kim, total=total)

    def test_order_view(self):
        o = self.order()
        self.assertEqual((o["id"], o["customer"], o["total"], o["status"], o["version"]),
                         ("order_0001", self.kim, 4500, "open", 1))

    def test_bad_totals(self):
        for total in (0, -5, 12.5, "10", True, None):
            with self.subTest(total=total):
                with self.assertRaises(InvalidRequest) as ctx:
                    self.svc.call("order.create", customer=self.kim, total=total)
                self.assertEqual(ctx.exception.param, "total")

    def test_unknown_customer(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("order.create", customer="customer_9999", total=100)
        self.assertEqual(ctx.exception.param, "customer")

    def test_pay_once(self):
        o = self.order()
        paid = self.svc.call("order.pay", order=o["id"])
        self.assertEqual((paid["status"], paid["version"]), ("paid", 2))
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("order.pay", order=o["id"])
        self.assertEqual(ctx.exception.param, "order")

    def test_events(self):
        o = self.order()
        self.assertEqual(self.svc.bus.log[-1], {"type": "order.created", "data": {"order": o}})

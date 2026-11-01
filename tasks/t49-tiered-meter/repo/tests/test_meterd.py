import unittest

from meterd import Service
from meterd.clock import FixedClock
from meterd.errors import Conflict, InvalidRequest, NotFound


class MeterTest(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.acme = self.svc.call("customer.create", name="Acme")["id"]

    def record(self, meter, quantity, customer=None):
        return self.svc.call("usage.record", customer=customer or self.acme, meter=meter, quantity=quantity)

    def test_an_empty_period_is_just_the_fee(self):
        invoice = self.svc.call("period.close", customer=self.acme)
        self.assertEqual(invoice["id"], "invoice_0001")
        self.assertEqual(invoice["lines"], [{"invoice": "invoice_0001", "meter": "flat", "quantity": 1, "amount": 500}])
        self.assertEqual(invoice["total"], 500)

    def test_usage_lines_and_rounding(self):
        self.assertEqual(self.record("units", 3)["total"], 3)
        self.record("units", 1)
        invoice = self.svc.call("period.close", customer=self.acme)
        # 4 units at 12.5 cents is exactly 50 cents; 3 at 12.5 would be 37.5, which rounds up
        self.assertEqual([(l["meter"], l["quantity"], l["amount"]) for l in invoice["lines"]],
                         [("flat", 1, 500), ("units", 4, 50)])
        self.record("units", 3)
        self.assertEqual(self.svc.call("period.close", customer=self.acme)["lines"][1]["amount"], 38)

    def test_allowance(self):
        self.record("allowance", 1000)
        self.assertEqual(len(self.svc.call("period.close", customer=self.acme)["lines"]), 1)
        self.record("allowance", 1030)
        line = self.svc.call("period.close", customer=self.acme)["lines"][1]
        self.assertEqual((line["quantity"], line["amount"]), (1030, 45))

    def test_each_period_starts_empty_and_each_customer_is_separate(self):
        other = self.svc.call("customer.create", name="Beta")["id"]
        self.record("units", 10)
        self.record("units", 20, other)
        self.svc.call("period.close", customer=self.acme)
        self.assertEqual(self.record("units", 1)["total"], 1)
        self.assertEqual(self.record("units", 1, other)["total"], 21)

    def test_events_come_in_a_set_order(self):
        self.record("units", 4)
        self.svc.bus.log.clear()
        self.svc.call("period.close", customer=self.acme)
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["invoice.created", "line.added", "line.added"])

    def test_errors(self):
        with self.assertRaises(NotFound):
            self.record("units", 1, "customer_9999")
        with self.assertRaises(InvalidRequest):
            self.record("nope", 1)
        with self.assertRaises(InvalidRequest):
            self.record("units", 0)
        with self.assertRaises(Conflict):
            self.record("flat", 1)


if __name__ == "__main__":
    unittest.main()

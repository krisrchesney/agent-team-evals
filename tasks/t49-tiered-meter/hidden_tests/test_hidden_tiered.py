"""Hidden tests for t49-tiered-meter. Every rule is shown by the starting code; see AUDIT.md."""
import unittest

from meterd import Service
from meterd.clock import FixedClock
from meterd.errors import InvalidRequest, MeterError, NotFound


class Base(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.acme = self.call("customer.create", name="Acme")["id"]
        self.beta = self.call("customer.create", name="Beta")["id"]

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def record(self, meter, quantity, customer=None):
        return self.call("usage.record", customer=customer or self.acme, meter=meter, quantity=quantity)

    def close(self, customer=None):
        return self.call("period.close", customer=customer or self.acme)

    def tiered_line(self, invoice):
        lines = [line for line in invoice["lines"] if line["meter"] == "tiered"]
        return lines[0] if lines else None

    def types(self):
        return [e["type"] for e in self.svc.bus.log]


class TestPricing(Base):
    def test_the_meter_takes_usage(self):
        self.assertEqual(self.record("tiered", 4), {"customer": self.acme, "meter": "tiered", "quantity": 4, "total": 4})
        self.assertEqual(self.record("tiered", 6)["total"], 10)
        self.assertIn("tiered", [m.name for m in self.svc.meters])

    def test_the_usage_event_carries_the_returned_view(self):
        self.svc.bus.log.clear()
        view = self.record("tiered", 4)
        self.assertEqual(self.svc.bus.log, [{"type": "usage.recorded", "data": {"usage": view}}])

    def test_each_tier_has_its_price(self):
        for units, amount in ((1, 8), (3, 23), (7, 53), (99, 743), (100, 750), (101, 756), (120, 874),
                              (1000, 6330), (1001, 6335), (2000, 10830)):
            with self.subTest(units=units):
                self.record("tiered", units)
                line = self.tiered_line(self.close())
                self.assertEqual((line["quantity"], line["amount"]), (units, amount))

    def test_usage_adds_up_across_calls(self):
        self.record("tiered", 60)
        self.record("tiered", 60)
        line = self.tiered_line(self.close())
        self.assertEqual((line["quantity"], line["amount"]), (120, 874))

    def test_half_a_cent_rounds_up_once_per_line(self):
        self.record("tiered", 3)
        self.assertEqual(self.tiered_line(self.close())["amount"], 23)

    def test_no_usage_means_no_line(self):
        invoice = self.close()
        self.assertIsNone(self.tiered_line(invoice))
        self.assertEqual([line["meter"] for line in invoice["lines"]], ["flat"])
        self.assertEqual(invoice["total"], 500)

    def test_the_line_is_last_and_counts_in_the_total(self):
        self.record("tiered", 10)
        self.record("allowance", 1010)
        self.record("units", 4)
        invoice = self.close()
        self.assertEqual([line["meter"] for line in invoice["lines"]], ["flat", "units", "allowance", "tiered"])
        self.assertEqual([line["amount"] for line in invoice["lines"]], [500, 50, 15, 75])
        self.assertEqual(invoice["total"], 640)
        self.assertEqual(self.call("invoice.retrieve", invoice=invoice["id"]), invoice)

    def test_the_line_names_its_invoice(self):
        self.record("tiered", 10)
        invoice = self.close()
        self.assertEqual(self.tiered_line(invoice), {"invoice": invoice["id"], "meter": "tiered", "quantity": 10, "amount": 75})

    def test_the_events_of_a_close_come_in_order(self):
        self.record("units", 4)
        self.record("tiered", 10)
        self.svc.bus.log.clear()
        invoice = self.close()
        self.assertEqual(self.types(), ["invoice.created", "line.added", "line.added", "line.added"])
        self.assertEqual([e["data"]["line"] for e in self.svc.bus.log[1:]], invoice["lines"])
        self.assertEqual(self.svc.bus.log[0]["data"], {"invoice": invoice})

    def test_other_meters_do_not_feed_it(self):
        self.record("units", 50)
        self.record("allowance", 50)
        self.assertIsNone(self.tiered_line(self.close()))
        self.record("tiered", 5)
        invoice = self.close()
        self.assertEqual([line["meter"] for line in invoice["lines"]], ["flat", "tiered"])


class TestPeriods(Base):
    def test_a_new_period_starts_empty(self):
        self.record("tiered", 150)
        self.close()
        self.assertEqual(self.record("tiered", 10)["total"], 10)
        line = self.tiered_line(self.close())
        self.assertEqual((line["quantity"], line["amount"]), (10, 75))

    def test_a_period_after_a_used_one_can_have_no_line(self):
        self.record("tiered", 150)
        self.close()
        self.assertIsNone(self.tiered_line(self.close()))

    def test_closing_one_customer_leaves_the_others_alone(self):
        self.record("tiered", 40)
        self.record("tiered", 60, self.beta)
        self.close(self.acme)
        self.assertEqual(self.record("tiered", 1, self.beta)["total"], 61)
        self.assertEqual(self.record("tiered", 1)["total"], 1)
        self.assertEqual(self.tiered_line(self.close(self.beta))["quantity"], 61)

    def test_services_do_not_share_usage(self):
        other = Service(clock=FixedClock())
        cust = other.call("customer.create", name="Acme")["id"]
        self.record("tiered", 10)
        self.assertEqual(other.call("usage.record", customer=cust, meter="tiered", quantity=5)["total"], 5)

    def test_closing_a_customer_with_no_usage_changes_nothing_later(self):
        self.close()
        self.assertEqual(self.record("tiered", 2)["total"], 2)


class TestChecks(Base):
    def test_bad_quantities_change_nothing(self):
        self.record("tiered", 5)
        for bad in (0, -1, 1.5, "3", True, None, 1_000_001):
            with self.assertRaises(InvalidRequest) as ctx:
                self.call("usage.record", customer=self.acme, meter="tiered", quantity=bad)
            self.assertEqual(ctx.exception.param, "quantity")
        self.assertEqual(self.record("tiered", 1)["total"], 6)

    def test_customer_and_meter_are_checked_in_order(self):
        with self.assertRaises(NotFound) as ctx:
            self.call("usage.record", customer="customer_9999", meter="nope", quantity=1)
        self.assertEqual(ctx.exception.param, "customer")
        with self.assertRaises(InvalidRequest) as ctx:
            self.call("usage.record", customer=self.acme, meter="nope", quantity=0)
        self.assertEqual(ctx.exception.param, "meter")
        self.assertIsInstance(ctx.exception, MeterError)

    def test_failed_calls_emit_nothing(self):
        self.svc.bus.log.clear()
        with self.assertRaises(MeterError):
            self.call("usage.record", customer=self.acme, meter="tiered", quantity=0)
        self.assertEqual(self.types(), [])


class TestExisting(Base):
    def test_the_other_meters_are_unchanged(self):
        self.record("units", 3)
        self.record("allowance", 1030)
        invoice = self.close()
        self.assertEqual([(l["meter"], l["quantity"], l["amount"]) for l in invoice["lines"]],
                         [("flat", 1, 500), ("units", 3, 38), ("allowance", 1030, 45)])

    def test_flat_still_takes_no_usage(self):
        with self.assertRaises(MeterError):
            self.record("flat", 1)


if __name__ == "__main__":
    unittest.main()

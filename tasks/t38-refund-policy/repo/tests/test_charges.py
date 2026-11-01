import unittest

from payledger import Service
from payledger.clock import FixedClock
from payledger.errors import InvalidRequest, NotFound


class ChargeTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.charge = self.svc.call("charge.create", customer="cus-1", amount=2500, tax=200, description="Mug")

    def test_create(self):
        c = self.charge
        self.assertEqual((c["id"], c["amount"], c["tax"], c["refunded"], c["status"]),
                         ("charge_0001", 2500, 200, 0, "succeeded"))
        self.assertEqual((c["created_at"], c["version"]), ("2026-01-05T09:00:00Z", 1))

    def test_ledger_has_the_charge(self):
        rows = self.svc.call("ledger.entries", charge=self.charge["id"])["data"]
        self.assertEqual([(r["kind"], r["amount"], r["ref"]) for r in rows], [("charge", 2500, "Mug")])

    def test_event(self):
        self.assertEqual(self.svc.bus.log[0]["type"], "charge.created")
        self.assertEqual(self.svc.bus.log[0]["data"]["charge"], self.charge)

    def test_tax_cannot_exceed_amount(self):
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.call("charge.create", customer="c", amount=100, tax=101)
        self.assertEqual(ctx.exception.param, "tax")

    def test_unknown_charge(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("charge.retrieve", charge="charge_9999")
        self.assertEqual(ctx.exception.param, "charge")

    def test_list_by_customer(self):
        self.svc.call("charge.create", customer="cus-2", amount=100)
        out = self.svc.call("charge.list", customer="cus-2")
        self.assertEqual([c["customer"] for c in out["data"]], ["cus-2"])
        self.assertFalse(out["has_more"])

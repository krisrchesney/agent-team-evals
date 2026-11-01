import unittest

from billbook import Service
from billbook.clock import FixedClock
from billbook.errors import Conflict, InvalidRequest, NotFound


class InvoiceTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.inv = self.svc.call("invoice.create", customer="cus-1", amount=50000, due="2026-02-01")

    def test_create(self):
        i = self.inv
        self.assertEqual((i["id"], i["amount"], i["due"], i["paid"], i["balance"], i["status"], i["version"]),
                         ("invoice_0001", 50000, "2026-02-01", 0, 50000, "open", 1))

    def test_pay_in_pieces(self):
        self.clock.advance(minutes=1)
        out = self.svc.call("invoice.pay", invoice=self.inv["id"], amount=20000)
        self.assertEqual((out["paid"], out["balance"], out["status"], out["version"]), (20000, 30000, "open", 2))
        out = self.svc.call("invoice.pay", invoice=self.inv["id"], amount=30000)
        self.assertEqual((out["balance"], out["status"]), (0, "paid"))
        self.assertEqual(len(self.svc.call("payment.list", invoice=self.inv["id"])["data"]), 2)

    def test_cannot_overpay_or_pay_twice(self):
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("invoice.pay", invoice=self.inv["id"], amount=50001)
        self.assertEqual(ctx.exception.param, "amount")
        self.svc.call("invoice.pay", invoice=self.inv["id"], amount=50000)
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("invoice.pay", invoice=self.inv["id"], amount=1)
        self.assertEqual(ctx.exception.param, "invoice")

    def test_bad_due_date(self):
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.call("invoice.create", customer="c", amount=100, due="02/01/2026")
        self.assertEqual(ctx.exception.param, "due")

    def test_unknown_invoice(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("invoice.retrieve", invoice="invoice_9999")
        self.assertEqual(ctx.exception.param, "invoice")

    def test_list_filters(self):
        self.svc.call("invoice.create", customer="cus-2", amount=100, due="2026-02-01")
        self.assertEqual(len(self.svc.call("invoice.list", customer="cus-2")["data"]), 1)
        self.assertEqual(len(self.svc.call("invoice.list", status="paid")["data"]), 0)

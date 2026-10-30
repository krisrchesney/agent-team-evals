import unittest

from paydesk import Context, Forbidden, InvalidRequest, Service

T0 = "2024-05-01T12:00:00+00:00"
ALL = frozenset({"charges:write", "charges:read"})


class ChargeTests(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=lambda: T0)
        self.ctx = Context(actor="user_1", scopes=ALL)

    def test_create_and_capture(self):
        charge = self.svc.call("charge.create", self.ctx, account="acct_1", amount=2500)
        self.assertEqual(charge["status"], "authorized")
        captured = self.svc.call("charge.capture", self.ctx, charge_id=charge["id"])
        self.assertEqual((captured["status"], captured["amount_captured"]), ("captured", 2500))
        self.assertEqual(self.svc.ledger.balance("merchant_revenue", "USD"), 2500)
        self.assertEqual(self.svc.events.types(), ["charge.created", "charge.captured"])

    def test_scope_is_checked(self):
        reader = Context(actor="user_2", scopes=frozenset({"charges:read"}))
        with self.assertRaises(Forbidden):
            self.svc.call("charge.create", reader, account="acct_1", amount=100)

    def test_bad_amount(self):
        with self.assertRaises(InvalidRequest) as cm:
            self.svc.call("charge.create", self.ctx, account="acct_1", amount=0)
        self.assertEqual((cm.exception.code, cm.exception.param), ("invalid_amount", "amount"))
        self.assertEqual(self.svc.events.types(), [])


if __name__ == "__main__":
    unittest.main()

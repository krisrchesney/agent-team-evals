"""Hidden tests for t19. Each test name names the repo document that states the rule:
api = docs/API.md, conv<N> = docs/CONVENTIONS.md item N, errors = docs/ERRORS.md,
ledger = docs/LEDGER.md, events = docs/EVENTS.md, reg = existing behaviour that must keep working.
"""
import itertools
import unittest

from paydesk import Conflict, Context, Forbidden, InvalidRequest, NotFound, Service
from paydesk import ops, reports

ALL = frozenset({"charges:write", "charges:read", "refunds:write", "refunds:read"})


def ticking_clock():
    seconds = itertools.count(0)
    return lambda: "2024-05-01T12:00:%02d+00:00" % next(seconds)


def plain_ids():
    counter = itertools.count(1)
    return lambda prefix: f"{prefix}_{next(counter)}"


class Base(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=ticking_clock(), ids=plain_ids())
        self.ctx = Context(actor="user_1", scopes=ALL)

    def call(self, name, ctx=None, **params):
        return self.svc.call(name, ctx or self.ctx, **params)

    def captured(self, amount=2500, currency="USD", capture=None, account="acct_1"):
        charge = self.call("charge.create", account=account, amount=amount, currency=currency)
        if capture is None:
            self.call("charge.capture", charge_id=charge["id"])
        else:
            self.call("charge.capture", charge_id=charge["id"], amount=capture)
        return charge["id"]

    def charge(self, charge_id):
        return self.call("charge.retrieve", charge_id=charge_id)

    def snapshot(self):
        return (len(self.svc.ledger.transactions), len(self.svc.audit.entries), len(self.svc.events.published),
                {cid: c.serialize() for cid, c in self.svc.store.charges.items()})

    def assertError(self, cls, code, param, name, **params):
        with self.assertRaises(cls) as cm:
            self.call(name, **params)
        self.assertEqual((cm.exception.code, cm.exception.param), (code, param), str(cm.exception))


class Api(Base):
    def test_api_operations_are_registered(self):
        self.assertIn("refund.create", ops.OPERATIONS)
        self.assertIn("refund.retrieve", ops.OPERATIONS)

    def test_api_full_refund_by_default(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid)
        self.assertEqual(refund["amount"], 2500)
        charge = self.charge(cid)
        self.assertEqual((charge["status"], charge["amount_refunded"], charge["refunds"]),
                         ("refunded", 2500, [refund["id"]]))

    def test_api_refund_object_shape(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid, amount=1000)
        self.assertEqual(refund, {"id": "re_2", "object": "refund", "charge": cid, "amount": 1000,
                                  "currency": "USD", "reason": "requested_by_customer",
                                  "status": "succeeded", "created": "2024-05-01T12:00:02+00:00"})

    def test_api_partial_then_rest(self):
        cid = self.captured(2500)
        first = self.call("refund.create", charge_id=cid, amount=1000)
        charge = self.charge(cid)
        self.assertEqual((charge["status"], charge["amount_refunded"]), ("partially_refunded", 1000))
        second = self.call("refund.create", charge_id=cid)
        self.assertEqual(second["amount"], 1500)
        charge = self.charge(cid)
        self.assertEqual((charge["status"], charge["amount_refunded"], charge["refunds"]),
                         ("refunded", 2500, [first["id"], second["id"]]))

    def test_api_several_partials_add_up_exactly(self):
        cid = self.captured(1000)
        for _ in range(3):
            self.call("refund.create", charge_id=cid, amount=300)
        self.assertEqual(self.charge(cid)["status"], "partially_refunded")
        self.call("refund.create", charge_id=cid, amount=100)
        self.assertEqual(self.charge(cid)["status"], "refunded")

    def test_api_default_amount_is_what_was_captured_not_authorized(self):
        cid = self.captured(2500, capture=1800)
        self.assertEqual(self.call("refund.create", charge_id=cid)["amount"], 1800)
        self.assertEqual(self.charge(cid)["status"], "refunded")

    def test_api_reasons(self):
        cid = self.captured(3000)
        for reason in ("duplicate", "fraudulent", "requested_by_customer"):
            self.assertEqual(self.call("refund.create", charge_id=cid, amount=1000, reason=reason)["reason"], reason)

    def test_api_currency_is_the_charges(self):
        cid = self.captured(5000, currency="JPY")
        self.assertEqual(self.call("refund.create", charge_id=cid, amount=500)["currency"], "JPY")

    def test_api_retrieve(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid, amount=700)
        self.call("refund.create", charge_id=cid, amount=100)
        self.assertEqual(self.call("refund.retrieve", refund_id=refund["id"]), refund)

    def test_api_scopes(self):
        cid = self.captured(2500)
        charges_only = Context(actor="user_2", scopes=frozenset({"charges:write", "charges:read"}))
        with self.assertRaises(Forbidden):
            self.call("refund.create", charges_only, charge_id=cid)
        writer = Context(actor="user_3", scopes=frozenset({"refunds:write"}))
        refund = self.call("refund.create", writer, charge_id=cid, amount=100)
        with self.assertRaises(Forbidden):
            self.call("refund.retrieve", writer, refund_id=refund["id"])
        reader = Context(actor="user_4", scopes=frozenset({"refunds:read"}))
        self.assertEqual(self.call("refund.retrieve", reader, refund_id=refund["id"]), refund)


class Errors(Base):
    def test_errors_bad_charge_id(self):
        for bad in ("", 5, None):
            with self.subTest(bad=bad):
                self.assertError(InvalidRequest, "invalid_param", "charge_id", "refund.create", charge_id=bad)

    def test_errors_bad_amount(self):
        cid = self.captured()
        for bad in (0, -5, True, 10.0, "100"):
            with self.subTest(bad=bad):
                self.assertError(InvalidRequest, "invalid_amount", "amount", "refund.create", charge_id=cid, amount=bad)

    def test_errors_bad_reason(self):
        cid = self.captured()
        for bad in ("angry", "", "Duplicate"):
            with self.subTest(bad=bad):
                self.assertError(InvalidRequest, "invalid_reason", "reason", "refund.create", charge_id=cid, reason=bad)

    def test_errors_unknown_charge(self):
        self.assertError(NotFound, "not_found", "charge_id", "refund.create", charge_id="ch_nope")

    def test_errors_not_captured(self):
        authorized = self.call("charge.create", account="acct_1", amount=100)["id"]
        self.assertError(InvalidRequest, "charge_not_captured", "charge_id", "refund.create", charge_id=authorized)
        voided = self.call("charge.create", account="acct_1", amount=100)["id"]
        self.call("charge.void", charge_id=voided)
        self.assertError(InvalidRequest, "charge_not_captured", "charge_id", "refund.create", charge_id=voided)

    def test_errors_already_refunded(self):
        cid = self.captured(500)
        self.call("refund.create", charge_id=cid)
        self.assertError(InvalidRequest, "charge_already_refunded", "charge_id", "refund.create", charge_id=cid)
        self.assertError(InvalidRequest, "charge_already_refunded", "charge_id", "refund.create",
                         charge_id=cid, amount=1)

    def test_errors_amount_too_large(self):
        cid = self.captured(2500)
        self.assertError(InvalidRequest, "amount_too_large", "amount", "refund.create", charge_id=cid, amount=2501)
        self.call("refund.create", charge_id=cid, amount=2000)
        self.assertError(InvalidRequest, "amount_too_large", "amount", "refund.create", charge_id=cid, amount=501)

    def test_errors_retrieve(self):
        self.assertError(NotFound, "not_found", "refund_id", "refund.retrieve", refund_id="re_nope")
        self.assertError(InvalidRequest, "invalid_param", "refund_id", "refund.retrieve", refund_id="")

    def test_errors_check_order(self):
        cid = self.captured(2500)
        # parameters in the order listed (charge_id, amount, reason)
        self.assertError(InvalidRequest, "invalid_param", "charge_id", "refund.create", charge_id="", amount=0)
        self.assertError(InvalidRequest, "invalid_amount", "amount", "refund.create", charge_id=cid, amount=0,
                         reason="angry")
        # parameters before existence
        self.assertError(InvalidRequest, "invalid_reason", "reason", "refund.create", charge_id="ch_nope",
                         reason="angry")
        # state before amounts
        authorized = self.call("charge.create", account="acct_1", amount=100)["id"]
        self.assertError(InvalidRequest, "charge_not_captured", "charge_id", "refund.create",
                         charge_id=authorized, amount=999)


class NoSideEffects(Base):
    def test_conv4_failures_change_nothing(self):
        cid = self.captured(2500)
        self.call("refund.create", charge_id=cid, amount=500)
        authorized = self.call("charge.create", account="acct_1", amount=100)["id"]
        before = self.snapshot()
        refunds_before = dict(getattr(self.svc.store, "refunds", {}))
        attempts = [dict(charge_id=cid, amount=5000), dict(charge_id=cid, amount=0),
                    dict(charge_id=cid, reason="angry"), dict(charge_id="ch_nope"),
                    dict(charge_id=authorized)]
        for params in attempts:
            with self.subTest(params=params):
                with self.assertRaises(InvalidRequest if params.get("charge_id") != "ch_nope" else NotFound):
                    self.call("refund.create", **params)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(dict(getattr(self.svc.store, "refunds", {})), refunds_before)

    def test_conv4_forbidden_changes_nothing(self):
        cid = self.captured(2500)
        before = self.snapshot()
        with self.assertRaises(Forbidden):
            self.call("refund.create", Context(actor="x", scopes=frozenset()), charge_id=cid)
        self.assertEqual(self.snapshot(), before)


class Idempotency(Base):
    def test_conv5_replay_returns_the_first_result_once(self):
        cid = self.captured(2500)
        keyed = self.ctx.with_key("k-1")
        first = self.call("refund.create", keyed, charge_id=cid, amount=1000)
        counts = self.snapshot()
        second = self.call("refund.create", keyed, charge_id=cid, amount=1000)
        self.assertEqual(second, first)
        self.assertEqual(self.snapshot(), counts)
        self.assertEqual(self.charge(cid)["amount_refunded"], 1000)

    def test_conv5_replay_after_the_charge_is_fully_refunded(self):
        cid = self.captured(2500)
        keyed = self.ctx.with_key("k-2")
        first = self.call("refund.create", keyed, charge_id=cid)
        self.assertEqual(self.call("refund.create", keyed, charge_id=cid), first)

    def test_conv5_key_reuse_with_other_params(self):
        cid = self.captured(2500)
        keyed = self.ctx.with_key("k-3")
        self.call("refund.create", keyed, charge_id=cid, amount=1000)
        before = self.snapshot()
        for params in (dict(charge_id=cid, amount=900), dict(charge_id=cid, amount=1000, reason="duplicate")):
            with self.subTest(params=params):
                with self.assertRaises(Conflict) as cm:
                    self.call("refund.create", keyed, **params)
                self.assertEqual(cm.exception.code, "idempotency_mismatch")
        self.assertEqual(self.snapshot(), before)

    def test_conv5_params_are_compared_as_passed(self):
        cid = self.captured(2500)
        keyed = self.ctx.with_key("k-4")
        self.call("refund.create", keyed, charge_id=cid, amount=1000)
        with self.assertRaises(Conflict):
            self.call("refund.create", keyed, charge_id=cid, amount=1000, reason="requested_by_customer")

    def test_conv5_failed_request_can_be_retried_with_the_same_key(self):
        cid = self.captured(2500)
        keyed = self.ctx.with_key("k-5")
        with self.assertRaises(InvalidRequest):
            self.call("refund.create", keyed, charge_id=cid, amount=9999)
        self.assertEqual(self.call("refund.create", keyed, charge_id=cid, amount=2500)["amount"], 2500)

    def test_conv5_retrieve_ignores_keys(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid, amount=100)
        keyed = self.ctx.with_key("k-7")
        self.assertEqual(self.call("refund.retrieve", keyed, refund_id=refund["id"]), refund)
        self.assertEqual(self.call("refund.create", keyed, charge_id=cid, amount=200)["amount"], 200)


class LedgerRules(Base):
    def test_ledger_full_refund_returns_the_money(self):
        cid = self.captured(2500, account="acct_9")
        refund = self.call("refund.create", charge_id=cid)
        self.assertEqual(self.svc.ledger.balance("merchant_revenue", "USD"), 0)
        self.assertEqual(self.svc.ledger.balance("customer:acct_9", "USD"), 0)
        txns = self.svc.ledger.for_ref(refund["id"])
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0]["currency"], "USD")
        self.assertEqual(sorted(txns[0]["entries"]), [("customer:acct_9", 2500), ("merchant_revenue", -2500)])

    def test_ledger_partial_refunds(self):
        cid = self.captured(2500, currency="EUR")
        a = self.call("refund.create", charge_id=cid, amount=1000)
        b = self.call("refund.create", charge_id=cid, amount=400)
        self.assertEqual(self.svc.ledger.balance("merchant_revenue", "EUR"), 1100)
        self.assertEqual(self.svc.ledger.balance("customer:acct_1", "EUR"), -1100)
        self.assertEqual([len(self.svc.ledger.for_ref(r["id"])) for r in (a, b)], [1, 1])
        self.assertEqual(len(self.svc.ledger.for_ref(cid)), 1)

    def test_ledger_revenue_report_nets_refunds(self):
        cid = self.captured(2500)
        self.captured(800, currency="JPY")
        self.call("refund.create", charge_id=cid, amount=1000)
        self.assertEqual(reports.revenue_by_currency(self.svc.ledger), {"JPY": 800, "USD": 1500})


class AuditRules(Base):
    def test_conv7_refund_is_audited(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid)
        entries = self.svc.audit.for_object(refund["id"])
        self.assertEqual(entries, [{"actor": "user_1", "action": "refund.create", "object_id": refund["id"],
                                    "at": refund["created"], "details": {"charge": cid, "amount": 2500}}])

    def test_conv7_retrieve_is_not_audited(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid, amount=10)
        count = len(self.svc.audit.entries)
        self.call("refund.retrieve", refund_id=refund["id"])
        self.assertEqual(len(self.svc.audit.entries), count)

    def test_conv7_actor_is_the_caller(self):
        cid = self.captured(2500)
        agent = Context(actor="support_7", scopes=frozenset({"refunds:write"}))
        refund = self.call("refund.create", agent, charge_id=cid, amount=10)
        self.assertEqual(self.svc.audit.for_object(refund["id"])[0]["actor"], "support_7")


class EventRules(Base):
    def test_events_refund_emits_two_events_in_order(self):
        cid = self.captured(2500)
        start = len(self.svc.events.published)
        refund = self.call("refund.create", charge_id=cid, amount=1000)
        new = self.svc.events.published[start:]
        self.assertEqual([e["type"] for e in new], ["refund.created", "charge.refunded"])
        self.assertEqual(new[0]["data"], refund)
        self.assertEqual(new[1]["data"], self.charge(cid))
        self.assertEqual(new[1]["data"]["status"], "partially_refunded")
        self.assertEqual(new[1]["data"]["refunds"], [refund["id"]])

    def test_events_retrieve_emits_nothing(self):
        cid = self.captured(2500)
        refund = self.call("refund.create", charge_id=cid, amount=1000)
        count = len(self.svc.events.published)
        self.call("refund.retrieve", refund_id=refund["id"])
        self.assertEqual(len(self.svc.events.published), count)


class OneClockReading(Base):
    def test_conv9_one_time_for_the_whole_operation(self):
        cid = self.captured(2500)
        start = len(self.svc.events.published)
        refund = self.call("refund.create", charge_id=cid, amount=1000)
        times = {refund["created"], self.svc.audit.for_object(refund["id"])[0]["at"]}
        times |= {e["created"] for e in self.svc.events.published[start:]}
        self.assertEqual(len(times), 1, times)

    def test_conv9_ids_come_from_the_service(self):
        cid = self.captured(2500)
        self.assertEqual(self.call("refund.create", charge_id=cid, amount=1)["id"], "re_2")
        self.assertEqual(self.call("refund.create", charge_id=cid, amount=1)["id"], "re_3")


class Regression(Base):
    def test_reg_charges_still_work(self):
        cid = self.captured(2500)
        self.assertEqual(self.charge(cid)["status"], "captured")
        other = self.call("charge.create", account="acct_2", amount=100)["id"]
        self.assertEqual(self.call("charge.void", charge_id=other)["status"], "voided")
        with self.assertRaises(InvalidRequest):
            self.call("charge.capture", charge_id=cid)

    def test_reg_unknown_operation(self):
        with self.assertRaises(NotFound) as cm:
            self.call("refund.cancel", charge_id="x")
        self.assertEqual(cm.exception.code, "unknown_operation")


if __name__ == "__main__":
    unittest.main()

import unittest

from addrbook import Service
from addrbook.clock import FixedClock
from addrbook.errors import InvalidRequest, NotFound


class ContactTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.ada = self.svc.call("contact.create", name="Ada", emails=["ada@example.com"], company="Engine Co")

    def test_create(self):
        a = self.ada
        self.assertEqual((a["id"], a["name"], a["emails"], a["phones"], a["company"], a["version"]),
                         ("contact_0001", "Ada", ["ada@example.com"], [], "Engine Co", 1))

    def test_update_replaces_given_fields(self):
        self.clock.advance(minutes=3)
        out = self.svc.call("contact.update", contact=self.ada["id"], phones=["+44 20 7946 0000"])
        self.assertEqual((out["phones"], out["emails"], out["version"]), (["+44 20 7946 0000"], ["ada@example.com"], 2))
        self.assertEqual(out["updated_at"], "2026-01-05T09:03:00Z")

    def test_bad_email(self):
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.call("contact.create", name="X", emails=["nope"])
        self.assertEqual(ctx.exception.param, "emails")

    def test_activity_log_and_list(self):
        self.svc.call("activity.log", contact=self.ada["id"], kind="call", note="hi")
        self.clock.advance(minutes=1)
        self.svc.call("activity.log", contact=self.ada["id"], kind="email")
        rows = self.svc.call("activity.list", contact=self.ada["id"])["data"]
        self.assertEqual([(r["kind"], r["note"]) for r in rows], [("call", "hi"), ("email", "")])

    def test_unknown_contact(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("activity.list", contact="contact_9999")
        self.assertEqual(ctx.exception.param, "contact")

    def test_list_by_company_ignores_case(self):
        self.svc.call("contact.create", name="Bob", company="Other")
        out = self.svc.call("contact.list", company="engine co")
        self.assertEqual([c["name"] for c in out["data"]], ["Ada"])

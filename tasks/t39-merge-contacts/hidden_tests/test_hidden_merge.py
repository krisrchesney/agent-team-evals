"""Hidden tests for t39-merge-contacts. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from addrbook import Service
from addrbook.clock import FixedClock
from addrbook.errors import BookError, Conflict, InvalidRequest, NotFound

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.a = self.make("Ada Lovelace", emails=["ada@example.com"], phones=["+44 20 7946 0001"], company="Engine Co")
        self.b = self.make("A. Lovelace", emails=["ADA@example.com", "ada@work.org"],
                           phones=["+44 (20) 7946-0001", "07700 900123"], company="Analytical Ltd")
        self.svc.bus.log.clear()

    def make(self, name, **kw):
        return self.svc.call("contact.create", name=name, **kw)["id"]

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def merge(self, primary=None, duplicate=None):
        return self.call("contact.merge", primary=primary or self.a, duplicate=duplicate or self.b)

    def get(self, cid):
        return self.call("contact.retrieve", contact=cid)

    def acts(self, cid):
        return self.call("activity.list", contact=cid)["data"]

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, BookError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestBasics(Base):
    def test_operation_is_registered(self):
        self.assertIn("contact.merge", self.svc.operations())
        self.assertIn("contact.update", self.svc.operations())

    def test_returns_the_primary_view(self):
        out = self.merge()
        self.assertEqual(out["id"], self.a)
        self.assertEqual(out, self.get(self.a))

    def test_primary_is_bumped(self):
        self.clock.advance(minutes=7)
        out = self.merge()
        self.assertEqual((out["version"], out["updated_at"]), (2, "2026-01-05T09:07:00Z"))
        self.assertEqual(out["created_at"], T0)

    def test_event(self):
        out = self.merge()
        (ev,) = self.svc.bus.log
        self.assertEqual(ev["type"], "contact.merged")
        self.assertEqual(ev["data"]["contact"], out)
        self.assertEqual(ev["data"]["duplicate"], self.get(self.b))

    def test_unknown_contacts(self):
        self.assertError(NotFound, "contact", "contact.merge", primary="contact_9999", duplicate=self.b)
        self.assertError(NotFound, "contact", "contact.merge", primary=self.a, duplicate="contact_9999")

    def test_missing_arguments(self):
        self.assertError(InvalidRequest, "primary", "contact.merge", duplicate=self.b)
        self.assertError(InvalidRequest, "duplicate", "contact.merge", primary=self.a)

    def test_arguments_are_stripped(self):
        out = self.call("contact.merge", primary=f" {self.a} ", duplicate=f"{self.b}  ")
        self.assertEqual(out["id"], self.a)

    def test_failures_change_nothing(self):
        self.assertIn("contact.merge", self.svc.operations())
        before = (self.get(self.a), self.get(self.b))
        for params in ({"primary": self.a, "duplicate": self.a}, {"primary": self.a, "duplicate": "nope"},
                       {"primary": "nope", "duplicate": self.b}):
            with self.assertRaises(BookError):
                self.call("contact.merge", **params)
        self.assertEqual((self.get(self.a), self.get(self.b)), before)
        self.assertEqual(self.svc.bus.log, [])

    def test_other_contacts_untouched(self):
        c = self.make("Cy", emails=["cy@example.com"])
        before = self.get(c)
        self.merge()
        self.assertEqual(self.get(c), before)


class TestWinner(Base):
    """answers.json: winner"""

    def test_newer_duplicate_wins(self):
        self.clock.advance(hours=1)
        self.call("contact.update", contact=self.b, name="Augusta Ada")
        out = self.merge()
        self.assertEqual((out["name"], out["company"]), ("Augusta Ada", "Analytical Ltd"))

    def test_newer_primary_wins(self):
        self.clock.advance(hours=1)
        self.call("contact.update", contact=self.a, company="Engine Co 2")
        out = self.merge()
        self.assertEqual((out["name"], out["company"]), ("Ada Lovelace", "Engine Co 2"))

    def test_tie_goes_to_primary(self):
        out = self.merge()
        self.assertEqual((out["name"], out["company"]), ("Ada Lovelace", "Engine Co"))

    def test_tie_goes_to_primary_either_way_round(self):
        out = self.merge(primary=self.b, duplicate=self.a)
        self.assertEqual((out["name"], out["company"]), ("A. Lovelace", "Analytical Ltd"))

    def test_blank_never_replaces(self):
        self.clock.advance(hours=1)
        c = self.make("Cy")                       # no company, newest
        out = self.merge(primary=self.a, duplicate=c)
        self.assertEqual(out["company"], "Engine Co")
        self.assertEqual(out["name"], "Cy")

    def test_blank_company_filled_from_other(self):
        c = self.make("Cy", company="Zed")
        self.clock.advance(hours=1)
        self.call("contact.update", contact=self.a, name="Ada L")
        d = self.make("Di")
        out = self.merge(primary=d, duplicate=c)
        self.assertEqual(out["company"], "Zed")

    def test_decided_by_updated_at_not_created_at(self):
        self.clock.advance(hours=1)
        self.call("contact.update", contact=self.a, name="Ada Updated")   # a is older but updated later
        out = self.merge(primary=self.b, duplicate=self.a)
        self.assertEqual(out["name"], "Ada Updated")


class TestLists(Base):
    """answers.json: lists"""

    def test_emails_union_ignoring_case(self):
        out = self.merge()
        self.assertEqual(out["emails"], ["ada@example.com", "ada@work.org"])

    def test_first_seen_spelling_is_kept(self):
        out = self.merge(primary=self.b, duplicate=self.a)
        self.assertEqual(out["emails"], ["ADA@example.com", "ada@work.org"])

    def test_phones_compared_by_digits(self):
        out = self.merge()
        self.assertEqual(out["phones"], ["+44 20 7946 0001", "07700 900123"])

    def test_same_digits_collapse(self):
        c = self.make("Cy", phones=["555-0100"])
        d = self.make("Di", phones=["(555) 0100", "555 0199"])
        out = self.merge(primary=c, duplicate=d)
        self.assertEqual(out["phones"], ["555-0100", "555 0199"])

    def test_order_primary_first_then_new(self):
        c = self.make("Cy", emails=["z@x.io", "a@x.io"])
        d = self.make("Di", emails=["m@x.io", "A@X.io", "b@x.io"])
        out = self.merge(primary=c, duplicate=d)
        self.assertEqual(out["emails"], ["z@x.io", "a@x.io", "m@x.io", "b@x.io"])

    def test_empty_lists(self):
        c, d = self.make("Cy"), self.make("Di")
        out = self.merge(primary=c, duplicate=d)
        self.assertEqual((out["emails"], out["phones"]), ([], []))

    def test_duplicate_keeps_its_own_lists(self):
        self.merge()
        dup = self.get(self.b)
        self.assertEqual(dup["emails"], ["ADA@example.com", "ada@work.org"])
        self.assertEqual(dup["phones"], ["+44 (20) 7946-0001", "07700 900123"])

    def test_lists_are_copies(self):
        out = self.merge()
        out["emails"].append("hack@x.io")
        self.assertEqual(len(self.get(self.a)["emails"]), 2)


class TestDuplicateRecord(Base):
    """answers.json: duplicate_record"""

    def test_status_fields_on_every_view(self):
        v = self.get(self.a)
        self.assertEqual((v["status"], v["merged_into"]), ("active", None))
        self.assertEqual(self.call("contact.list")["data"][0]["status"], "active")

    def test_duplicate_becomes_a_tombstone(self):
        self.clock.advance(minutes=2)
        self.merge()
        d = self.get(self.b)
        self.assertEqual((d["status"], d["merged_into"]), ("merged", self.a))
        self.assertEqual((d["version"], d["updated_at"]), (2, "2026-01-05T09:02:00Z"))

    def test_primary_stays_active(self):
        out = self.merge()
        self.assertEqual((out["status"], out["merged_into"]), ("active", None))

    def test_not_listed_any_more(self):
        self.merge()
        ids = [c["id"] for c in self.call("contact.list")["data"]]
        self.assertEqual(ids, [self.a])

    def test_list_limit_counts_only_active(self):
        c = self.make("Cy")
        self.merge()
        out = self.call("contact.list", limit=2)
        self.assertEqual(([x["id"] for x in out["data"]], out["has_more"]), ([self.a, c], False))

    def test_cannot_update_merged(self):
        self.merge()
        self.assertError(Conflict, "contact", "contact.update", contact=self.b, name="Zed")

    def test_cannot_log_activity_on_merged(self):
        self.merge()
        self.assertError(Conflict, "contact", "activity.log", contact=self.b, kind="call")

    def test_cannot_merge_a_merged_duplicate_again(self):
        c = self.make("Cy")
        self.merge()
        self.assertError(Conflict, "duplicate", "contact.merge", primary=c, duplicate=self.b)

    def test_cannot_merge_into_a_merged_primary(self):
        c = self.make("Cy")
        self.merge()
        self.assertError(Conflict, "primary", "contact.merge", primary=self.b, duplicate=c)

    def test_self_merge_is_invalid(self):
        self.assertError(InvalidRequest, "duplicate", "contact.merge", primary=self.a, duplicate=self.a)

    def test_merge_conflict_changes_nothing(self):
        c = self.make("Cy")
        self.merge()
        before = self.get(self.a)
        self.svc.bus.log.clear()
        with self.assertRaises(Conflict):
            self.call("contact.merge", primary=self.a, duplicate=self.b)
        self.assertEqual(self.get(self.a), before)
        self.assertEqual(self.svc.bus.log, [])


class TestActivities(Base):
    """answers.json: activities"""

    def setUp(self):
        super().setUp()
        self.a1 = self.call("activity.log", contact=self.a, kind="call", note="first")["id"]
        self.clock.advance(minutes=10)
        self.b1 = self.call("activity.log", contact=self.b, kind="meeting", note="second")["id"]
        self.clock.advance(minutes=10)
        self.a2 = self.call("activity.log", contact=self.a, kind="email")["id"]
        self.svc.bus.log.clear()

    def test_activities_move_to_primary_in_time_order(self):
        self.merge()
        rows = self.acts(self.a)
        self.assertEqual([r["id"] for r in rows], [self.a1, self.b1, self.a2])
        self.assertEqual({r["contact"] for r in rows}, {self.a})

    def test_moved_activity_keeps_everything_else(self):
        self.merge()
        moved = [r for r in self.acts(self.a) if r["id"] == self.b1][0]
        self.assertEqual((moved["kind"], moved["note"], moved["at"]), ("meeting", "second", "2026-01-05T09:10:00Z"))

    def test_duplicate_list_is_empty(self):
        self.merge()
        self.assertEqual(self.acts(self.b), [])

    def test_ties_ordered_by_id(self):
        c = self.make("Cy")
        d = self.make("Di")
        x = self.call("activity.log", contact=d, kind="call")["id"]
        y = self.call("activity.log", contact=c, kind="call")["id"]
        self.merge(primary=c, duplicate=d)
        self.assertEqual([r["id"] for r in self.acts(c)], [x, y])

    def test_merge_logs_no_activity(self):
        before = self.svc.ids.new("activity")
        self.merge()
        after = self.svc.ids.new("activity")
        self.assertEqual(int(after.split("_")[1]), int(before.split("_")[1]) + 1)
        self.assertEqual(len(self.acts(self.a)), 3)

    def test_new_activity_after_merge_goes_to_primary(self):
        self.merge()
        new = self.call("activity.log", contact=self.a, kind="call")["id"]
        self.assertEqual(self.acts(self.a)[-1]["id"], new)

    def test_activity_event_stream_untouched(self):
        self.merge()
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["contact.merged"])


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        self.assertEqual(len(self.call("contact.list")["data"]), 2)
        out = self.call("contact.update", contact=self.a, company="X")
        self.assertEqual((out["company"], out["version"]), ("X", 2))
        self.assertEqual(self.acts(self.a), [])


if __name__ == "__main__":
    unittest.main()

"""Hidden tests for t32-soft-delete. Test names carry the requirement number; see AUDIT.md."""
import json
import unittest
from datetime import datetime

from deskly.clock import FixedClock
from deskly.desk import Desk
from deskly.errors import Conflict, InvalidInput, NotFound

T0 = "2026-03-01T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(datetime(2026, 3, 1, 9, 0))
        self.d = Desk(clock=self.clock)
        self.ann = self.d.create_customer("Ann", "ann@example.com")["id"]
        self.bob = self.d.create_customer("Bob", "bob@example.com")["id"]

    def ticket(self, customer=None, subject="Printer jams", body="Paper stuck", **kw):
        return self.d.open_ticket(customer or self.ann, subject, body, **kw)["id"]

    def comment(self, ticket, text="Still broken", author="Ann"):
        return self.d.add_comment(ticket, author, text)["id"]

    def tick(self, **delta):
        self.clock.advance(**(delta or {"minutes": 5}))

    def stamp(self):
        return self.clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def ids(self, listing):
        return [r["id"] for r in listing["data"]]

    def assertGone(self, call, param, *args, **kw):
        with self.assertRaises(NotFound) as ctx:
            call(*args, **kw)
        self.assertEqual(ctx.exception.param, param)

    def assertConflict(self, param, call, *args, **kw):
        with self.assertRaises(Conflict) as ctx:
            call(*args, **kw)
        self.assertEqual(ctx.exception.param, param)


class TestSoftDelete(Base):
    def test_r1_delete_returns_the_view(self):
        t1 = self.ticket()
        self.assertIsNone(self.d.get_ticket(t1)["deleted_at"])
        self.assertIsNone(self.d.get_customer(self.ann)["deleted_at"])
        t2 = self.ticket(subject="Second")
        m1 = self.comment(t2)
        self.assertIsNone(self.d.list_comments(t2)["data"][0]["deleted_at"])
        self.tick()
        view = self.d.delete_ticket(t1)
        self.assertEqual((view["id"], view["subject"], view["deleted_at"]), (t1, "Printer jams",
                                                                              "2026-03-01T09:05:00Z"))
        self.tick()
        self.assertEqual(self.d.delete_comment(m1)["deleted_at"], "2026-03-01T09:10:00Z")
        self.tick()
        view = self.d.delete_customer(self.ann)
        self.assertEqual((view["id"], view["email"], view["deleted_at"]), (self.ann, "ann@example.com",
                                                                            "2026-03-01T09:15:00Z"))

    def test_r1_a_deleted_ticket_is_not_found(self):
        t1 = self.ticket()
        self.d.delete_ticket(t1)
        for call in (lambda: self.d.get_ticket(t1), lambda: self.d.set_status(t1, "closed"),
                     lambda: self.d.add_tag(t1, "x"), lambda: self.d.remove_tag(t1, "x"),
                     lambda: self.d.add_comment(t1, "Ann", "hi"), lambda: self.d.list_comments(t1),
                     lambda: self.d.delete_ticket(t1)):
            self.assertGone(call, "ticket")

    def test_r1_a_deleted_comment_is_not_found(self):
        m1 = self.comment(self.ticket())
        self.d.delete_comment(m1)
        self.assertGone(self.d.delete_comment, "comment", m1)

    def test_r1_a_deleted_customer_is_not_found(self):
        self.d.delete_customer(self.ann)
        for call in (lambda: self.d.get_customer(self.ann), lambda: self.d.update_customer(self.ann, name="X"),
                     lambda: self.d.open_ticket(self.ann, "s", "b"), lambda: self.d.list_tickets(customer=self.ann),
                     lambda: self.d.customer_summary(self.ann), lambda: self.d.delete_customer(self.ann),
                     lambda: self.d.merge_customers(self.ann, self.bob),
                     lambda: self.d.merge_customers(self.bob, self.ann)):
            self.assertGone(call, "customer")
        self.assertGone(self.d.find_customer, "email", "ann@example.com")

    def test_r1_one_event_per_delete_with_the_old_data(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.comment(t1, "second")
        self.d.delete_comment(m1)
        self.assertEqual(self.d.activity(1)[0]["type"], "comment.deleted")
        self.assertEqual(self.d.activity(1)[0]["data"], {"id": m1})
        before = len(self.d.activity(100))
        self.d.delete_ticket(t1)
        self.assertEqual(len(self.d.activity(100)), before + 1)
        self.assertEqual((self.d.activity(1)[0]["type"], self.d.activity(1)[0]["data"]),
                         ("ticket.deleted", {"id": t1, "comments": 1}))
        t2 = self.ticket(self.bob)
        self.ticket(self.bob, subject="Other")
        before = len(self.d.activity(100))
        self.d.delete_customer(self.bob)
        self.assertEqual(len(self.d.activity(100)), before + 1)
        self.assertEqual((self.d.activity(1)[0]["type"], self.d.activity(1)[0]["data"]),
                         ("customer.deleted", {"id": self.bob, "tickets": 2}))
        self.assertTrue(t2)

    def test_r2_customer_delete_cascades(self):
        t1, t2, t3 = self.ticket(), self.ticket(subject="Second"), self.ticket(self.bob)
        m1, m2 = self.comment(t1), self.comment(t2)
        self.tick()
        self.d.delete_customer(self.ann)
        for ticket in (t1, t2):
            self.assertEqual(self.d.get_ticket(ticket, include_deleted=True)["deleted_at"], self.stamp())
        for c in self.d.list_comments(t1, include_deleted=True)["data"]:
            self.assertEqual(c["deleted_at"], self.stamp())
        self.assertIsNone(self.d.get_ticket(t3)["deleted_at"])
        self.assertEqual(self.d.stats()["deleted"], {"customers": 1, "tickets": 2, "comments": 2})
        self.assertTrue(m1 and m2)

    def test_r2_rows_deleted_earlier_keep_their_own_time(self):
        t1, t2 = self.ticket(), self.ticket(subject="Second")
        m1, m2 = self.comment(t2), self.comment(t2, "other")
        self.tick()
        self.d.delete_ticket(t1)
        early = self.stamp()
        self.tick()
        self.d.delete_comment(m1)
        self.tick(minutes=20)
        self.d.delete_customer(self.ann)
        late = self.stamp()
        self.assertEqual(self.d.get_ticket(t1, include_deleted=True)["deleted_at"], early)
        self.assertEqual(self.d.get_ticket(t2, include_deleted=True)["deleted_at"], late)
        times = {c["id"]: c["deleted_at"] for c in self.d.list_comments(t2, include_deleted=True)["data"]}
        self.assertEqual(times, {m1: "2026-03-01T09:10:00Z", m2: late})

    def test_r2_ticket_delete_cascades_to_comments(self):
        t1 = self.ticket()
        self.comment(t1)
        self.comment(t1, "more")
        self.tick()
        self.d.delete_ticket(t1)
        got = self.d.list_comments(t1, include_deleted=True)["data"]
        self.assertEqual([c["deleted_at"] for c in got], [self.stamp()] * 2)
        self.assertEqual(self.d.stats()["comments"], 0)


class TestRestore(Base):
    def test_r3_restore_ticket(self):
        t1 = self.ticket(tags=["hardware"])
        self.comment(t1, "printer on fire")
        self.comment(t1, "second note")
        score = self.d.search_tickets("printer")[0]["score"]
        self.d.delete_ticket(t1)
        view = self.d.restore_ticket(t1)
        self.assertEqual((view["deleted_at"], view["comment_count"]), (None, 2))
        self.assertEqual(self.d.get_ticket(t1)["tags"], ["hardware"])
        self.assertEqual(len(self.d.list_comments(t1)["data"]), 2)
        self.assertEqual(self.d.search_tickets("printer")[0]["score"], score)
        self.assertEqual((self.d.activity(1)[0]["type"], self.d.activity(1)[0]["data"]),
                         ("ticket.restored", {"id": t1, "comments": 2}))
        self.assertEqual(self.d.stats()["deleted"], {"customers": 0, "tickets": 0, "comments": 0})

    def test_r3_a_restore_returns_only_what_went_with_it(self):
        t1 = self.ticket()
        m1, m2 = self.comment(t1, "first"), self.comment(t1, "second")
        self.tick()
        self.d.delete_comment(m1)
        self.tick()
        self.d.delete_ticket(t1)
        self.d.restore_ticket(t1)
        self.assertEqual([c["id"] for c in self.d.list_comments(t1)["data"]], [m2])
        self.assertEqual(self.d.get_ticket(t1)["comment_count"], 1)
        self.assertEqual(self.d.activity(1)[0]["data"], {"id": t1, "comments": 1})
        self.assertEqual(self.d.search_tickets("first"), [])

    def test_r3_restore_customer(self):
        t1, t2 = self.ticket(), self.ticket(subject="Second one")
        m1 = self.comment(t1, "note")
        self.tick()
        self.d.delete_ticket(t2)
        self.tick()
        self.d.delete_customer(self.ann)
        view = self.d.restore_customer(self.ann)
        self.assertEqual((view["deleted_at"], view["ticket_count"]), (None, 1))
        self.assertEqual(self.d.get_ticket(t1)["comment_count"], 1)
        self.assertGone(self.d.get_ticket, "ticket", t2)
        self.assertEqual(self.d.find_customer("ann@example.com")["id"], self.ann)
        self.assertEqual((self.d.activity(1)[0]["type"], self.d.activity(1)[0]["data"]),
                         ("customer.restored", {"id": self.ann, "tickets": 1}))
        self.assertEqual([h["ticket"] for h in self.d.search_tickets("note")], [t1])
        self.assertTrue(m1)

    def test_r3_restore_a_cascaded_ticket_with_its_customer_only(self):
        t1 = self.ticket()
        self.d.delete_customer(self.ann)
        self.assertConflict("customer", self.d.restore_ticket, t1)
        self.assertGone(self.d.get_ticket, "ticket", t1)
        self.d.restore_customer(self.ann)
        self.assertIsNone(self.d.get_ticket(t1)["deleted_at"])

    def test_r3_restoring_something_live_is_a_conflict(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.assertConflict("customer", self.d.restore_customer, self.ann)
        self.assertConflict("ticket", self.d.restore_ticket, t1)
        self.assertConflict("comment", self.d.restore_comment, m1)

    def test_r3_a_comment_needs_a_live_ticket(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.d.delete_comment(m1)
        self.d.delete_ticket(t1)
        self.assertConflict("ticket", self.d.restore_comment, m1)
        self.d.restore_ticket(t1)
        self.assertEqual(self.d.list_comments(t1)["data"], [])      # m1 was deleted on its own
        view = self.d.restore_comment(m1)
        self.assertIsNone(view["deleted_at"])
        self.assertEqual(self.d.get_ticket(t1)["comment_count"], 1)
        self.assertEqual((self.d.activity(1)[0]["type"], self.d.activity(1)[0]["data"]),
                         ("comment.restored", {"id": m1}))

    def test_r3_restore_customer_with_a_taken_email_changes_nothing(self):
        t1 = self.ticket()
        self.d.delete_customer(self.ann)
        self.d.create_customer("New Ann", "ann@example.com")
        before = self.d.stats()
        self.assertConflict("email", self.d.restore_customer, self.ann)
        self.assertEqual(self.d.stats(), before)
        self.assertGone(self.d.get_ticket, "ticket", t1)
        self.assertEqual(self.d.get_customer(self.ann, include_deleted=True)["deleted_at"], T0)

    def test_r3_unknown_ids(self):
        self.assertGone(self.d.restore_customer, "customer", "c99")
        self.assertGone(self.d.restore_ticket, "ticket", "t99")
        self.assertGone(self.d.restore_comment, "comment", "m99")


class TestEmail(Base):
    def test_r4_a_deleted_email_can_be_used_again(self):
        self.d.delete_customer(self.ann)
        new = self.d.create_customer("Ann II", "ANN@example.com")
        self.assertEqual(self.d.find_customer("ann@example.com")["id"], new["id"])
        self.assertConflict("email", self.d.update_customer, self.bob, email="ann@example.com")
        self.assertConflict("email", self.d.create_customer, "Third", "ann@example.com")

    def test_r4_update_to_a_deleted_customers_email(self):
        self.d.delete_customer(self.bob)
        self.assertEqual(self.d.update_customer(self.ann, email="bob@example.com")["email"], "bob@example.com")
        self.assertEqual(self.d.find_customer("bob@example.com")["id"], self.ann)
        self.assertGone(self.d.find_customer, "email", "ann@example.com")

    def test_r4_the_email_index_follows_restore(self):
        self.d.delete_customer(self.ann)
        self.d.restore_customer(self.ann)
        self.assertConflict("email", self.d.create_customer, "Dup", "ann@example.com")
        self.assertEqual(self.d.find_customer("ann@example.com")["id"], self.ann)


class TestReads(Base):
    def setUp(self):
        super().setUp()
        self.t1 = self.ticket(subject="Printer jams", tags=["hardware", "urgent"])
        self.t2 = self.ticket(subject="Login broken", body="Cannot log in", tags=["urgent"], priority=3)
        self.t3 = self.ticket(self.bob, subject="Slow printer", tags=["hardware"])
        self.m1 = self.comment(self.t1, "printer printer")
        self.m2 = self.comment(self.t1, "turned it off")
        self.m3 = self.comment(self.t3, "ink low")
        self.tick()

    def test_r5_lists(self):
        self.d.delete_ticket(self.t2)
        self.d.delete_comment(self.m2)
        self.assertEqual(self.ids(self.d.list_tickets()), [self.t3, self.t1])
        self.assertEqual(self.ids(self.d.list_tickets(customer=self.ann)), [self.t1])
        self.assertEqual(self.ids(self.d.list_tickets(tag="urgent")), [self.t1])
        self.assertEqual(self.ids(self.d.list_tickets(status="open")), [self.t3, self.t1])
        self.assertEqual(self.ids(self.d.list_comments(self.t1)), [self.m1])
        self.d.delete_customer(self.bob)
        self.assertEqual(self.ids(self.d.list_customers()), [self.ann])
        self.assertEqual(self.ids(self.d.list_tickets(tag="hardware")), [self.t1])
        self.assertFalse(self.d.list_tickets(limit=1)["has_more"])

    def test_r5_counts_in_views(self):
        self.assertEqual((self.d.get_ticket(self.t1)["comment_count"], self.d.get_customer(self.ann)["ticket_count"]),
                         (2, 2))
        self.d.delete_comment(self.m1)
        self.d.delete_ticket(self.t2)
        self.assertEqual(self.d.get_ticket(self.t1)["comment_count"], 1)
        self.assertEqual(self.d.get_customer(self.ann)["ticket_count"], 1)
        self.assertEqual(self.d.list_customers()["data"][0]["ticket_count"], 1)
        self.assertEqual(self.d.list_tickets(customer=self.ann)["data"][0]["comment_count"], 1)

    def test_r5_search(self):
        before = {h["ticket"]: h["score"] for h in self.d.search_tickets("printer")}
        self.assertEqual(before, {self.t1: 5, self.t3: 3})
        self.d.delete_comment(self.m1)
        self.assertEqual({h["ticket"]: h["score"] for h in self.d.search_tickets("printer")},
                         {self.t1: 3, self.t3: 3})
        self.d.restore_comment(self.m1)
        self.assertEqual({h["ticket"]: h["score"] for h in self.d.search_tickets("printer")}, before)
        self.d.delete_ticket(self.t3)
        self.assertEqual([h["ticket"] for h in self.d.search_tickets("printer")], [self.t1])
        self.d.delete_comment(self.m2)
        self.assertEqual(self.d.search_tickets("turned"), [])

    def test_r5_a_ticket_found_only_through_a_deleted_comment_disappears(self):
        self.assertEqual([h["ticket"] for h in self.d.search_tickets("ink")], [self.t3])
        self.d.delete_comment(self.m3)
        self.assertEqual(self.d.search_tickets("ink"), [])
        self.d.restore_comment(self.m3)
        self.assertEqual([h["ticket"] for h in self.d.search_tickets("ink")], [self.t3])

    def test_r5_search_after_a_customer_round_trip(self):
        self.d.delete_customer(self.ann)
        self.assertEqual([h["ticket"] for h in self.d.search_tickets("printer")], [self.t3])
        self.d.restore_customer(self.ann)
        self.assertEqual({h["ticket"]: h["score"] for h in self.d.search_tickets("printer")},
                         {self.t1: 5, self.t3: 3})

    def test_r5_reports(self):
        self.d.set_status(self.t2, "closed")
        self.d.delete_ticket(self.t1)
        self.assertEqual(self.d.status_counts(), {"open": 1, "pending": 0, "closed": 1})
        self.assertEqual(self.d.tag_counts(), [{"tag": "hardware", "count": 1}, {"tag": "urgent", "count": 1}])
        self.assertEqual(self.d.customer_summary(self.ann), {"customer": self.ann, "tickets": 1, "open": 0,
                                                             "comments": 0})
        self.assertEqual(self.d.customer_summary(self.bob), {"customer": self.bob, "tickets": 1, "open": 1,
                                                             "comments": 1})
        self.clock.advance(days=3)
        self.assertEqual(self.d.aging(), {"0-1": 0, "2-7": 1, "8-30": 0, "31+": 0})
        self.assertEqual([(c["name"], c["open"]) for c in self.d.busiest_customers()], [("Bob", 1)])
        self.assertEqual(self.d.stats(), {"customers": 2, "tickets": 2, "comments": 1,
                                          "deleted": {"customers": 0, "tickets": 1, "comments": 2}})

    def test_r5_busiest_customers_skips_a_deleted_customer(self):
        self.d.delete_customer(self.ann)
        self.assertEqual([(c["name"], c["open"]) for c in self.d.busiest_customers()], [("Bob", 1)])
        self.assertEqual(self.d.stats()["deleted"], {"customers": 1, "tickets": 2, "comments": 2})
        self.assertEqual(self.d.tag_counts(), [{"tag": "hardware", "count": 1}])

    def test_r5_exports(self):
        self.d.delete_ticket(self.t2)
        lines = self.d.tickets_csv().splitlines()
        self.assertEqual([l.split(",")[0] for l in lines[1:]], [self.t1, self.t3])
        self.assertEqual(lines[0], "id,customer,subject,status,priority,tags,created_at")
        self.assertIn("c1,Ann,ann@example.com,1,", self.d.customers_csv())
        self.d.delete_customer(self.bob)
        self.assertEqual([l.split(",")[0] for l in self.d.customers_csv().splitlines()[1:]], [self.ann])
        self.assertEqual([l.split(",")[0] for l in self.d.tickets_csv().splitlines()[1:]], [self.t1])

    def test_r6_include_deleted(self):
        self.d.delete_ticket(self.t2)
        self.d.delete_comment(self.m2)
        self.d.delete_customer(self.bob)
        self.assertEqual(self.d.get_ticket(self.t2, include_deleted=True)["deleted_at"], self.stamp())
        self.assertEqual(self.ids(self.d.list_tickets(include_deleted=True)), [self.t3, self.t2, self.t1])
        self.assertEqual(self.ids(self.d.list_tickets(customer=self.bob, include_deleted=True)), [self.t3])
        self.assertEqual(self.ids(self.d.list_tickets(tag="urgent", include_deleted=True)), [self.t2, self.t1])
        self.assertEqual(self.ids(self.d.list_comments(self.t1, include_deleted=True)), [self.m1, self.m2])
        self.assertEqual(self.ids(self.d.list_customers(include_deleted=True)), [self.ann, self.bob])
        self.assertEqual(self.d.get_customer(self.bob, include_deleted=True)["deleted_at"], self.stamp())
        self.assertEqual(self.d.get_customer(self.bob, include_deleted=True)["ticket_count"], 0)
        self.assertEqual(self.d.get_ticket(self.t1, include_deleted=True)["comment_count"], 1)
        self.assertEqual(self.d.list_tickets(include_deleted=True, limit=2)["has_more"], True)

    def test_r6_include_deleted_for_missing_rows(self):
        self.assertGone(self.d.get_ticket, "ticket", "t99", include_deleted=True)
        self.assertGone(self.d.get_customer, "customer", "c99", include_deleted=True)
        self.assertGone(self.d.list_comments, "ticket", "t99", include_deleted=True)

    def test_r6_csv_with_deleted_rows(self):
        self.d.delete_ticket(self.t2)
        lines = self.d.tickets_csv(include_deleted=True).splitlines()
        self.assertEqual(lines[0], "id,customer,subject,status,priority,tags,created_at,deleted_at")
        by_id = {l.split(",")[0]: l for l in lines[1:]}
        self.assertTrue(by_id[self.t2].endswith(",2026-03-01T09:05:00Z"))
        self.assertTrue(by_id[self.t1].endswith(","))
        self.d.delete_customer(self.bob)
        rows = self.d.customers_csv(include_deleted=True).splitlines()
        self.assertEqual(rows[0], "id,name,email,tickets,created_at,deleted_at")
        self.assertTrue(rows[2].startswith("c2,Bob,bob@example.com,0,"))
        self.assertTrue(rows[2].endswith(",2026-03-01T09:05:00Z"))
        self.assertTrue(rows[1].endswith(","))
        self.assertIn("c1,Ann,ann@example.com,1,", rows[1])


class TestMergeAndTags(Base):
    def test_r7_merge_moves_deleted_tickets_too(self):
        t1, t2, t3 = self.ticket(), self.ticket(self.bob, subject="Two"), self.ticket(self.bob, subject="Three")
        self.d.delete_ticket(t3)
        view = self.d.merge_customers(self.ann, self.bob)
        events = self.d.activity(2)
        self.assertEqual(view["ticket_count"], 2)
        self.assertEqual(self.d.get_ticket(t3, include_deleted=True)["customer"], self.ann)
        self.assertEqual(self.ids(self.d.list_tickets(customer=self.ann)), [t2, t1])
        self.assertEqual(self.d.restore_ticket(t3)["deleted_at"], None)
        self.assertGone(self.d.get_customer, "customer", self.bob)
        self.assertEqual(self.d.get_customer(self.bob, include_deleted=True)["ticket_count"], 0)
        self.assertEqual(events[0]["data"], {"id": self.bob, "into": self.ann, "moved": 2})
        self.assertNotEqual(events[1]["type"], "customer.deleted")
        self.assertEqual(self.d.create_customer("Bob again", "bob@example.com")["ticket_count"], 0)

    def test_r7_restoring_the_merged_away_customer_does_not_take_tickets_back(self):
        t2 = self.ticket(self.bob, subject="Two")
        self.d.merge_customers(self.ann, self.bob)
        self.d.restore_customer(self.bob)
        self.assertEqual(self.d.get_ticket(t2)["customer"], self.ann)
        self.assertEqual(self.d.get_customer(self.bob)["ticket_count"], 0)

    def test_r8_rename_tag_reaches_deleted_tickets(self):
        t1 = self.ticket(tags=["urgent"])
        t2 = self.ticket(subject="Two", tags=["urgent", "hardware"])
        self.d.delete_ticket(t2)
        self.assertEqual(self.d.rename_tag("urgent", "p1"), {"renamed": 1})
        self.assertEqual(self.d.activity(1)[0]["data"], {"from": "urgent", "to": "p1", "tickets": 1})
        self.assertEqual(self.d.tag_counts(), [{"tag": "p1", "count": 1}])
        self.assertEqual(self.d.get_ticket(t2, include_deleted=True)["tags"], ["hardware", "p1"])
        self.d.restore_ticket(t2)
        self.assertEqual(self.ids(self.d.list_tickets(tag="p1")), [t2, t1])
        self.assertEqual(self.d.list_tickets(tag="urgent")["data"], [])
        self.assertEqual(self.d.rename_tag("p1", "p2"), {"renamed": 2})

    def test_r8_a_rename_with_only_deleted_tickets(self):
        t1 = self.ticket(tags=["old"])
        self.d.delete_ticket(t1)
        self.assertEqual(self.d.rename_tag("old", "new"), {"renamed": 0})
        self.d.restore_ticket(t1)
        self.assertEqual(self.d.get_ticket(t1)["tags"], ["new"])

    def test_r9_the_feed_keeps_everything(self):
        t1 = self.ticket()
        self.d.delete_ticket(t1)
        self.d.restore_ticket(t1)
        self.d.delete_ticket(t1)
        self.assertEqual([e["type"] for e in self.d.activity(4)],
                         ["ticket.deleted", "ticket.restored", "ticket.deleted", "ticket.opened"])


class TestTrash(Base):
    def test_r9_listing_order_and_shape(self):
        t1, t2 = self.ticket(subject="First"), self.ticket(subject="Second")
        m1 = self.comment(t1, "x" * 60)
        self.tick()
        self.d.delete_comment(m1)                       # 09:05
        self.tick()
        self.d.delete_ticket(t2)                        # 09:10
        self.tick()
        self.d.delete_customer(self.bob)                # 09:15
        got = self.d.trash()
        self.assertFalse(got["has_more"])
        self.assertEqual([(i["kind"], i["id"], i["label"], i["deleted_at"]) for i in got["data"]],
                         [("customer", self.bob, "Bob", "2026-03-01T09:15:00Z"),
                          ("ticket", t2, "Second", "2026-03-01T09:10:00Z"),
                          ("comment", m1, "x" * 40, "2026-03-01T09:05:00Z")])
        self.assertEqual(set(got["data"][0]), {"kind", "id", "label", "deleted_at"})

    def test_r9_ties_and_cascaded_rows(self):
        t1, t2 = self.ticket(subject="First"), self.ticket(subject="Second")
        m1, m2 = self.comment(t1, "one"), self.comment(t2, "two")
        self.d.delete_customer(self.ann)
        got = [(i["kind"], i["id"]) for i in self.d.trash()["data"]]
        self.assertEqual(got, [("customer", self.ann), ("ticket", t1), ("ticket", t2), ("comment", m1),
                               ("comment", m2)])

    def test_r9_filters_and_limits(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.d.delete_customer(self.ann)
        self.assertEqual([i["id"] for i in self.d.trash(kind="ticket")["data"]], [t1])
        self.assertEqual([i["id"] for i in self.d.trash(kind="comment")["data"]], [m1])
        page = self.d.trash(limit=2)
        self.assertEqual((len(page["data"]), page["has_more"]), (2, True))
        with self.assertRaises(InvalidInput) as ctx:
            self.d.trash(kind="order")
        self.assertEqual(ctx.exception.param, "kind")

    def test_r9_restored_rows_leave_the_trash(self):
        t1 = self.ticket()
        self.d.delete_ticket(t1)
        self.assertEqual(len(self.d.trash()["data"]), 1)
        self.d.restore_ticket(t1)
        self.assertEqual(self.d.trash()["data"], [])


class TestPurge(Base):
    def test_r10_purge_a_ticket(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.d.delete_ticket(t1)
        self.assertEqual(self.d.purge("ticket", t1), {"id": t1, "purged": True})
        self.assertGone(self.d.get_ticket, "ticket", t1, include_deleted=True)
        self.assertEqual(self.d.stats()["deleted"], {"customers": 0, "tickets": 0, "comments": 0})
        self.assertEqual((self.d.activity(1)[0]["type"], self.d.activity(1)[0]["data"]), ("ticket.purged", {"id": t1}))
        self.assertGone(self.d.restore_ticket, "ticket", t1)
        self.assertEqual(self.d.trash()["data"], [])
        self.assertTrue(m1)

    def test_r10_purge_a_comment(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.d.delete_comment(m1)
        self.assertEqual(self.d.purge("comment", m1), {"id": m1, "purged": True})
        self.assertEqual(self.d.activity(1)[0]["type"], "comment.purged")
        self.assertEqual(self.d.list_comments(t1, include_deleted=True)["data"], [])

    def test_r10_purge_a_customer_takes_everything_with_it(self):
        t1, t2 = self.ticket(), self.ticket(subject="Two")
        self.comment(t1)
        m2 = self.comment(t2)
        self.d.delete_comment(m2)                        # deleted on its own, before the customer
        self.d.delete_ticket(t2)
        self.d.delete_customer(self.ann)
        self.assertEqual(self.d.purge("customer", self.ann), {"id": self.ann, "purged": True})
        self.assertEqual(self.d.stats(), {"customers": 1, "tickets": 0, "comments": 0,
                                          "deleted": {"customers": 0, "tickets": 0, "comments": 0}})
        self.assertGone(self.d.get_ticket, "ticket", t2, include_deleted=True)
        self.assertEqual(self.d.activity(1)[0]["type"], "customer.purged")
        self.assertEqual(self.d.create_customer("Ann II", "ann@example.com")["id"], "c3")

    def test_r10_a_purge_keeps_the_rest_of_the_index_intact(self):
        t1 = self.ticket(tags=["a"])
        t2 = self.ticket(subject="Second", tags=["a"])
        self.d.delete_ticket(t1)
        self.d.purge("ticket", t1)
        self.assertEqual(self.ids(self.d.list_tickets(tag="a")), [t2])
        self.assertEqual(self.d.get_customer(self.ann)["ticket_count"], 1)
        self.assertEqual(self.d.rename_tag("a", "b"), {"renamed": 1})
        self.assertEqual(self.d.search_tickets("second")[0]["ticket"], t2)

    def test_r10_errors(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.assertConflict("ticket", self.d.purge, "ticket", t1)
        self.assertConflict("customer", self.d.purge, "customer", self.ann)
        self.assertConflict("comment", self.d.purge, "comment", m1)
        self.assertGone(self.d.purge, "ticket", "ticket", "t99")
        self.assertGone(self.d.purge, "customer", "customer", "c99")
        with self.assertRaises(InvalidInput) as ctx:
            self.d.purge("order", "o1")
        self.assertEqual(ctx.exception.param, "kind")
        self.assertEqual(self.d.get_ticket(t1)["id"], t1)

    def test_r10_ids_are_never_reused(self):
        t1 = self.ticket()
        self.d.delete_ticket(t1)
        self.d.purge("ticket", t1)
        self.assertEqual(self.ticket(), "t2")
        m1 = self.comment("t2")
        self.d.delete_comment(m1)
        self.d.purge("comment", m1)
        self.assertEqual(self.comment("t2"), "m2")


class TestRetention(Base):
    def test_r11_exactly_thirty_days_stays(self):
        t1 = self.ticket()
        self.d.delete_ticket(t1)
        self.clock.advance(days=30)
        self.assertEqual(self.d.purge_expired(), {"purged": {"customers": 0, "tickets": 0, "comments": 0}})
        self.assertEqual(self.d.get_ticket(t1, include_deleted=True)["id"], t1)
        self.assertNotEqual(self.d.activity(1)[0]["type"], "trash.purged")
        self.clock.advance(seconds=1)
        self.assertEqual(self.d.purge_expired(), {"purged": {"customers": 0, "tickets": 1, "comments": 0}})
        self.assertGone(self.d.get_ticket, "ticket", t1, include_deleted=True)

    def test_r11_a_customer_goes_with_everything_that_belongs_to_it(self):
        t1 = self.ticket()
        self.comment(t1)
        self.comment(t1, "two")
        self.ticket(self.bob)
        self.d.delete_customer(self.ann)
        self.clock.advance(days=31)
        self.assertEqual(self.d.purge_expired(), {"purged": {"customers": 1, "tickets": 1, "comments": 2}})
        event = self.d.activity(1)[0]
        self.assertEqual((event["type"], event["data"]), ("trash.purged", {"customers": 1, "tickets": 1,
                                                                            "comments": 2}))
        self.assertEqual(self.d.stats(), {"customers": 1, "tickets": 1, "comments": 0,
                                          "deleted": {"customers": 0, "tickets": 0, "comments": 0}})

    def test_r11_old_rows_under_a_newer_delete_go_alone(self):
        t1 = self.ticket()
        t2 = self.ticket(subject="Two")
        m1 = self.comment(t2)
        self.d.delete_ticket(t1)                         # day 0
        self.d.delete_comment(m1)                        # day 0
        self.clock.advance(days=40)
        self.d.delete_customer(self.ann)                 # day 40: takes t2 with it
        self.assertEqual(self.d.purge_expired(), {"purged": {"customers": 0, "tickets": 1, "comments": 1}})
        self.assertEqual(self.d.get_customer(self.ann, include_deleted=True)["deleted_at"], self.stamp())
        self.assertEqual(self.d.get_ticket(t2, include_deleted=True)["deleted_at"], self.stamp())
        self.assertGone(self.d.get_ticket, "ticket", t1, include_deleted=True)

    def test_r11_a_comment_alone(self):
        t1 = self.ticket()
        m1 = self.comment(t1)
        self.comment(t1, "stays")
        self.d.delete_comment(m1)
        self.clock.advance(days=45)
        self.assertEqual(self.d.purge_expired(), {"purged": {"customers": 0, "tickets": 0, "comments": 1}})
        self.assertEqual(self.d.get_ticket(t1)["comment_count"], 1)

    def test_r11_live_rows_are_never_purged(self):
        self.ticket()
        self.clock.advance(days=400)
        self.assertEqual(self.d.purge_expired()["purged"], {"customers": 0, "tickets": 0, "comments": 0})
        self.assertEqual(self.d.stats()["tickets"], 1)


class TestSnapshot(Base):
    def test_r12_round_trip_keeps_deleted_rows_and_restore_rules(self):
        t1, t2 = self.ticket(tags=["a"]), self.ticket(subject="Two")
        m1, m2 = self.comment(t1, "alpha"), self.comment(t1, "beta")
        self.tick()
        self.d.delete_comment(m1)
        self.tick()
        self.d.delete_ticket(t2)
        self.tick()
        self.d.delete_customer(self.ann)
        copy = Desk.load(json.loads(json.dumps(self.d.dump())), clock=self.clock)
        self.assertEqual(copy.stats(), self.d.stats())
        self.assertEqual(copy.trash(), self.d.trash())
        self.assertEqual(copy.get_ticket(t2, include_deleted=True), self.d.get_ticket(t2, include_deleted=True))
        self.assertGone(copy.get_customer, "customer", self.ann)
        copy.restore_customer(self.ann)
        self.assertEqual([c["id"] for c in copy.list_comments(t1)["data"]], [m2])
        self.assertGone(copy.get_ticket, "ticket", t2)
        self.assertEqual(copy.search_tickets("beta")[0]["ticket"], t1)
        self.assertEqual(copy.search_tickets("alpha"), [])
        self.assertEqual(copy.restore_comment(m1)["deleted_at"], None)

    def test_r12_the_email_index_and_ids_survive(self):
        self.d.delete_customer(self.ann)
        copy = Desk.load(self.d.dump(), clock=self.clock)
        self.assertEqual(copy.create_customer("Ann II", "ann@example.com")["id"], "c3")
        self.assertConflict("email", copy.restore_customer, self.ann)
        self.assertConflict("email", copy.create_customer, "Bob2", "bob@example.com")

    def test_r12_purge_and_retention_work_after_load(self):
        t1 = self.ticket()
        self.comment(t1)
        self.d.delete_customer(self.ann)
        copy = Desk.load(self.d.dump(), clock=self.clock)
        copy.clock.advance(days=31)
        self.assertEqual(copy.purge_expired()["purged"], {"customers": 1, "tickets": 1, "comments": 1})

    def test_r12_older_dump_has_no_deleted_rows(self):
        old = {"version": 1, "ids": {"c": 1, "t": 1, "m": 1},
               "customers": [{"id": "c1", "name": "Ann", "email": "ann@example.com",
                              "created_at": "2026-03-01T09:00:00Z"}],
               "tickets": [{"id": "t1", "customer": "c1", "subject": "Printer jams", "body": "Paper stuck",
                            "status": "open", "priority": 2, "tags": ["a"], "created_at": "2026-03-01T09:00:00Z",
                            "updated_at": "2026-03-01T09:00:00Z"}],
               "comments": [{"id": "m1", "ticket": "t1", "author": "Ann", "text": "hello",
                             "created_at": "2026-03-01T09:00:00Z"}],
               "feed": []}
        copy = Desk.load(old, clock=self.clock)
        self.assertEqual(copy.stats(), {"customers": 1, "tickets": 1, "comments": 1,
                                        "deleted": {"customers": 0, "tickets": 0, "comments": 0}})
        self.assertIsNone(copy.get_ticket("t1")["deleted_at"])
        self.assertEqual(copy.search_tickets("hello")[0]["ticket"], "t1")
        copy.delete_ticket("t1")
        self.assertEqual(copy.restore_ticket("t1")["comment_count"], 1)


if __name__ == "__main__":
    unittest.main()

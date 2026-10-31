import unittest
from datetime import datetime

from deskly.clock import FixedClock
from deskly.desk import Desk
from deskly.errors import Conflict, InvalidInput, NotFound


class DeskTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(datetime(2026, 3, 1, 9, 0))
        self.d = Desk(clock=self.clock)
        self.ann = self.d.create_customer("Ann", "Ann@Example.com")["id"]
        self.bob = self.d.create_customer("Bob", "bob@example.com")["id"]

    def ticket(self, customer=None, subject="Printer jams", body="It jams on page two.", **kw):
        return self.d.open_ticket(customer or self.ann, subject, body, **kw)["id"]

    def test_customers(self):
        view = self.d.get_customer(self.ann)
        self.assertEqual((view["email"], view["ticket_count"]), ("ann@example.com", 0))
        with self.assertRaises(Conflict):
            self.d.create_customer("Other Ann", "ann@example.com")
        with self.assertRaises(NotFound):
            self.d.get_customer("c99")
        self.assertEqual(self.d.find_customer("BOB@example.com")["id"], self.bob)

    def test_update_customer_email_index(self):
        self.d.update_customer(self.ann, email="ann@work.test")
        self.assertEqual(self.d.find_customer("ann@work.test")["id"], self.ann)
        self.d.create_customer("New", "ann@example.com")
        with self.assertRaises(Conflict):
            self.d.update_customer(self.bob, email="ann@work.test")

    def test_tickets_and_filters(self):
        t1 = self.ticket(tags=["hardware", "urgent"])
        t2 = self.ticket(self.bob, subject="Login broken", body="Cannot log in.", priority=3, tags=["urgent"])
        self.d.set_status(t1, "closed")
        self.assertEqual([t["id"] for t in self.d.list_tickets()["data"]], [t2, t1])
        self.assertEqual([t["id"] for t in self.d.list_tickets(tag="urgent")["data"]], [t2, t1])
        self.assertEqual([t["id"] for t in self.d.list_tickets(customer=self.bob)["data"]], [t2])
        self.assertEqual([t["id"] for t in self.d.list_tickets(status="closed")["data"]], [t1])
        with self.assertRaises(InvalidInput):
            self.d.open_ticket(self.ann, "x", "y", priority=7)

    def test_tags(self):
        t1 = self.ticket(tags=["hardware"])
        self.d.add_tag(t1, "Urgent")
        self.assertEqual(self.d.get_ticket(t1)["tags"], ["hardware", "urgent"])
        self.assertEqual(self.d.rename_tag("urgent", "p1"), {"renamed": 1})
        self.assertEqual(self.d.get_ticket(t1)["tags"], ["hardware", "p1"])
        self.d.remove_tag(t1, "hardware")
        self.assertEqual(self.d.tag_counts(), [{"tag": "p1", "count": 1}])

    def test_comments_and_counts(self):
        t1 = self.ticket()
        self.d.add_comment(t1, "Ann", "Still broken after restart")
        m2 = self.d.add_comment(t1, "Support", "Please send a photo")["id"]
        self.assertEqual(self.d.get_ticket(t1)["comment_count"], 2)
        self.d.delete_comment(m2)
        self.assertEqual([c["author"] for c in self.d.list_comments(t1)["data"]], ["Ann"])
        self.assertEqual(self.d.customer_summary(self.ann), {"customer": self.ann, "tickets": 1, "open": 1,
                                                             "comments": 1})

    def test_search(self):
        t1 = self.ticket(subject="Printer jams", body="Paper stuck")
        t2 = self.ticket(self.bob, subject="Login broken", body="The printer is fine")
        self.d.add_comment(t2, "Bob", "printer printer")
        hits = self.d.search_tickets("printer")
        self.assertEqual([(h["ticket"], h["score"]) for h in hits], [(t1, 3), (t2, 3)])
        self.d.add_comment(t2, "Bob", "printer")
        self.assertEqual(self.d.search_tickets("printer")[0]["ticket"], t2)
        self.assertEqual(self.d.search_tickets("printer paper")[0]["ticket"], t1)

    def test_reports(self):
        t1 = self.ticket()
        self.ticket(self.bob)
        self.ticket(self.bob, subject="Another")
        self.d.set_status(t1, "pending")
        self.clock.advance(days=10)
        self.assertEqual(self.d.status_counts(), {"open": 2, "pending": 1, "closed": 0})
        self.assertEqual(self.d.aging(), {"0-1": 0, "2-7": 0, "8-30": 3, "31+": 0})
        self.assertEqual([(b["name"], b["open"]) for b in self.d.busiest_customers()], [("Bob", 2), ("Ann", 1)])
        self.assertEqual(self.d.stats(), {"customers": 2, "tickets": 3, "comments": 0,
                                          "deleted": {"customers": 0, "tickets": 0, "comments": 0}})

    def test_delete_and_merge(self):
        t1 = self.ticket()
        self.d.add_comment(t1, "Ann", "hello")
        self.d.delete_ticket(t1)
        with self.assertRaises(NotFound):
            self.d.get_ticket(t1)
        t2 = self.ticket(self.bob)
        self.d.merge_customers(self.ann, self.bob)
        self.assertEqual(self.d.get_ticket(t2)["customer"], self.ann)
        self.assertEqual(self.d.delete_customer(self.ann)["deleted_at"], "2026-03-01T09:00:00Z")
        self.assertEqual(self.d.stats(), {"customers": 0, "tickets": 0, "comments": 0,
                                          "deleted": {"customers": 2, "tickets": 2, "comments": 1}})

    def test_activity_and_exports(self):
        t1 = self.ticket()
        self.d.delete_ticket(t1)
        self.assertEqual([e["type"] for e in self.d.activity(2)], ["ticket.deleted", "ticket.opened"])
        self.ticket(self.bob)
        self.assertEqual(self.d.tickets_csv().splitlines()[1],
                         "t2,c2,Printer jams,open,2,,2026-03-01T09:00:00Z")
        self.assertIn("c2,Bob,bob@example.com,1,", self.d.customers_csv())

    def test_snapshot_round_trip(self):
        t1 = self.ticket(tags=["hardware"])
        self.d.add_comment(t1, "Ann", "photo attached")
        copy = Desk.load(self.d.dump(), clock=self.clock)
        self.assertEqual(copy.get_ticket(t1), self.d.get_ticket(t1))
        self.assertEqual(copy.search_tickets("photo"), self.d.search_tickets("photo"))
        self.assertEqual(copy.open_ticket(self.bob, "New", "one")["id"], "t2")
        with self.assertRaises(Conflict):
            copy.create_customer("Ann again", "ann@example.com")


if __name__ == "__main__":
    unittest.main()

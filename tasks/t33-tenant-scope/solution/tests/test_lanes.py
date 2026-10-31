import unittest
from datetime import datetime

from lanes import ratelimit
from lanes.clock import FixedClock
from lanes.errors import Conflict, NotFound, QuotaExceeded, RateLimited
from lanes.service import Lanes


class LanesTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(datetime(2026, 3, 2, 9, 0))
        self.svc = Lanes(clock=self.clock)
        self.svc.create_tenant("acme", "Acme")
        self.p1 = self.svc.create_project("acme", "Website")["id"]
        self.ann = self.svc.add_member("acme", "Ann", "Ann@Example.com")["id"]
        self.bug = self.svc.add_label("acme", "bug", "#ff0000")["name"]

    def task(self, title="Fix the footer", **kw):
        return self.svc.create_task("acme", self.p1, title, **kw)["id"]

    def test_projects(self):
        self.assertEqual((self.p1, self.svc.get_project("acme", self.p1)["task_count"]), ("p1", 0))
        with self.assertRaises(Conflict):
            self.svc.create_project("acme", "website")
        self.svc.rename_project("acme", self.p1, "Site")
        self.assertEqual([p["name"] for p in self.svc.list_projects("acme")["data"]], ["Site"])
        self.svc.create_project("acme", "Website")

    def test_project_quota(self):
        for n in range(4):
            self.svc.create_project("acme", f"P{n}")
        with self.assertRaises(QuotaExceeded):
            self.svc.create_project("acme", "one too many")

    def test_members_and_labels(self):
        self.assertEqual(self.svc.get_member("acme", self.ann)["email"], "ann@example.com")
        with self.assertRaises(Conflict):
            self.svc.add_member("acme", "Other", "ann@example.com")
        with self.assertRaises(Conflict):
            self.svc.add_label("acme", "BUG")
        self.assertEqual(self.svc.list_labels("acme")["data"], [{"name": "bug", "color": "#ff0000"}])

    def test_task_lifecycle(self):
        t1 = self.task(assignee=self.ann, labels=["bug"], due="2026-03-01", priority=3)
        view = self.svc.get_task("acme", t1)
        self.assertEqual((view["status"], view["assignee"], view["labels"], view["due"]),
                         ("todo", self.ann, ["bug"], "2026-03-01"))
        self.clock.advance(minutes=5)
        self.svc.update_task("acme", t1, status="doing", title="Fix the header")
        self.assertEqual(self.svc.get_task("acme", t1)["title"], "Fix the header")
        self.assertEqual(self.svc.get_task("acme", t1)["updated_at"], "2026-03-02T09:05:00Z")
        self.svc.assign_task("acme", t1, None)
        self.assertIsNone(self.svc.get_task("acme", t1)["assignee"])
        self.svc.delete_task("acme", t1)
        with self.assertRaises(NotFound):
            self.svc.get_task("acme", t1)

    def test_task_filters_and_quota(self):
        t1, t2 = self.task(labels=["bug"]), self.task("Second", assignee=self.ann)
        self.svc.update_task("acme", t2, status="done")
        self.assertEqual([t["id"] for t in self.svc.list_tasks("acme", label="bug")["data"]], [t1])
        self.assertEqual([t["id"] for t in self.svc.list_tasks("acme", status="done", assignee=self.ann)["data"]], [t2])
        for n in range(18):
            self.task(f"Filler {n}")
        with self.assertRaises(QuotaExceeded):
            self.task("one too many")
        with self.assertRaises(NotFound):
            self.svc.list_tasks("acme", project="p9")

    def test_tags_comments_and_cache(self):
        t1 = self.task()
        self.assertEqual(self.svc.get_task("acme", t1)["labels"], [])
        self.svc.tag_task("acme", t1, "bug")
        self.assertEqual(self.svc.get_task("acme", t1)["labels"], ["bug"])
        self.svc.add_comment("acme", t1, self.ann, "Reproduced on Safari")
        self.assertEqual(self.svc.get_task("acme", t1)["comment_count"], 1)
        self.assertEqual(self.svc.list_comments("acme", t1)["data"][0]["author"], self.ann)
        self.svc.untag_task("acme", t1, "bug")
        self.assertEqual(self.svc.get_task("acme", t1)["labels"], [])

    def test_search(self):
        t1, t2 = self.task("Footer is broken"), self.task("Header spacing")
        self.svc.add_comment("acme", t2, self.ann, "footer too")
        self.assertEqual([(h["task"], h["score"]) for h in self.svc.search("acme", "footer")], [(t1, 2), (t2, 1)])
        self.svc.delete_task("acme", t1)
        self.assertEqual([h["task"] for h in self.svc.search("acme", "footer")], [t2])

    def test_reports(self):
        t1, t2 = self.task(assignee=self.ann, due="2026-03-01"), self.task("Second", labels=["bug"])
        self.svc.update_task("acme", t2, status="doing")
        self.assertEqual(self.svc.project_summary("acme", self.p1)["doing"], 1)
        self.svc.update_task("acme", t2, status="done")
        self.assertEqual(self.svc.project_summary("acme", self.p1)["done"], 1)
        self.assertEqual(self.svc.workload("acme"), [{"member": self.ann, "name": "Ann", "open": 1}])
        self.assertEqual([o["task"] for o in self.svc.overdue("acme")], [t1])
        self.assertEqual(self.svc.label_counts("acme"), [{"label": "bug", "count": 1}])

    def test_project_delete_and_member_removal(self):
        t1 = self.task(assignee=self.ann)
        self.assertEqual(self.svc.remove_member("acme", self.ann), {"id": self.ann, "removed": True})
        self.assertIsNone(self.svc.get_task("acme", t1)["assignee"])
        self.svc.delete_project("acme", self.p1)
        with self.assertRaises(NotFound):
            self.svc.get_task("acme", t1)
        self.assertEqual(self.svc.search("acme", "footer"), [])

    def test_outbox_audit_and_exports(self):
        t1 = self.task()
        events = self.svc.drain("acme")
        self.assertEqual([e["type"] for e in events], ["project.created", "member.added", "label.added",
                                                       "task.created"])
        self.assertEqual(self.svc.drain("acme"), [])
        self.assertEqual(self.svc.audit_log("acme", 1)[0]["action"], "task.create")
        self.assertEqual(self.svc.export_tasks_csv("acme", self.p1).splitlines()[1], f"{t1},Fix the footer,todo,,,,2")
        self.assertEqual(len(self.svc.export_json("acme")["tasks"]), 1)

    def test_rate_limit(self):
        for _ in range(ratelimit.RATE_LIMIT - 3):       # three calls were made in setUp
            self.svc.list_projects("acme")
        with self.assertRaises(RateLimited):
            self.svc.list_projects("acme")
        self.clock.advance(seconds=61)
        self.svc.list_projects("acme")

    def test_snapshot_round_trip(self):
        t1 = self.task(assignee=self.ann, labels=["bug"])
        self.svc.add_comment("acme", t1, self.ann, "hello world")
        copy = Lanes.load(self.svc.dump(), clock=self.clock)
        self.assertEqual(copy.get_task("acme", t1), self.svc.get_task("acme", t1))
        self.assertEqual(copy.search("acme", "hello")[0]["task"], t1)
        self.assertEqual(copy.create_project("acme", "Another")["id"], "p2")
        with self.assertRaises(Conflict):
            copy.add_member("acme", "Dup", "ann@example.com")


if __name__ == "__main__":
    unittest.main()

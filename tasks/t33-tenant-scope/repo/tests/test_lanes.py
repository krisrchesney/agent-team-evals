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
        self.p1 = self.svc.create_project("Website")["id"]
        self.ann = self.svc.add_member("Ann", "Ann@Example.com")["id"]
        self.bug = self.svc.add_label("bug", "#ff0000")["name"]

    def task(self, title="Fix the footer", **kw):
        return self.svc.create_task(self.p1, title, **kw)["id"]

    def test_projects(self):
        self.assertEqual((self.p1, self.svc.get_project(self.p1)["task_count"]), ("p1", 0))
        with self.assertRaises(Conflict):
            self.svc.create_project("website")
        self.svc.rename_project(self.p1, "Site")
        self.assertEqual([p["name"] for p in self.svc.list_projects()["data"]], ["Site"])
        self.svc.create_project("Website")

    def test_project_quota(self):
        for n in range(4):
            self.svc.create_project(f"P{n}")
        with self.assertRaises(QuotaExceeded):
            self.svc.create_project("one too many")

    def test_members_and_labels(self):
        self.assertEqual(self.svc.get_member(self.ann)["email"], "ann@example.com")
        with self.assertRaises(Conflict):
            self.svc.add_member("Other", "ann@example.com")
        with self.assertRaises(Conflict):
            self.svc.add_label("BUG")
        self.assertEqual(self.svc.list_labels()["data"], [{"name": "bug", "color": "#ff0000"}])

    def test_task_lifecycle(self):
        t1 = self.task(assignee=self.ann, labels=["bug"], due="2026-03-01", priority=3)
        view = self.svc.get_task(t1)
        self.assertEqual((view["status"], view["assignee"], view["labels"], view["due"]),
                         ("todo", self.ann, ["bug"], "2026-03-01"))
        self.clock.advance(minutes=5)
        self.svc.update_task(t1, status="doing", title="Fix the header")
        self.assertEqual(self.svc.get_task(t1)["title"], "Fix the header")
        self.assertEqual(self.svc.get_task(t1)["updated_at"], "2026-03-02T09:05:00Z")
        self.svc.assign_task(t1, None)
        self.assertIsNone(self.svc.get_task(t1)["assignee"])
        self.svc.delete_task(t1)
        with self.assertRaises(NotFound):
            self.svc.get_task(t1)

    def test_task_filters_and_quota(self):
        t1, t2 = self.task(labels=["bug"]), self.task("Second", assignee=self.ann)
        self.svc.update_task(t2, status="done")
        self.assertEqual([t["id"] for t in self.svc.list_tasks(label="bug")["data"]], [t1])
        self.assertEqual([t["id"] for t in self.svc.list_tasks(status="done", assignee=self.ann)["data"]], [t2])
        for n in range(18):
            self.task(f"Filler {n}")
        with self.assertRaises(QuotaExceeded):
            self.task("one too many")
        with self.assertRaises(NotFound):
            self.svc.list_tasks(project="p9")

    def test_tags_comments_and_cache(self):
        t1 = self.task()
        self.assertEqual(self.svc.get_task(t1)["labels"], [])
        self.svc.tag_task(t1, "bug")
        self.assertEqual(self.svc.get_task(t1)["labels"], ["bug"])
        self.svc.add_comment(t1, self.ann, "Reproduced on Safari")
        self.assertEqual(self.svc.get_task(t1)["comment_count"], 1)
        self.assertEqual(self.svc.list_comments(t1)["data"][0]["author"], self.ann)
        self.svc.untag_task(t1, "bug")
        self.assertEqual(self.svc.get_task(t1)["labels"], [])

    def test_search(self):
        t1, t2 = self.task("Footer is broken"), self.task("Header spacing")
        self.svc.add_comment(t2, self.ann, "footer too")
        self.assertEqual([(h["task"], h["score"]) for h in self.svc.search("footer")], [(t1, 2), (t2, 1)])
        self.svc.delete_task(t1)
        self.assertEqual([h["task"] for h in self.svc.search("footer")], [t2])

    def test_reports(self):
        t1, t2 = self.task(assignee=self.ann, due="2026-03-01"), self.task("Second", labels=["bug"])
        self.svc.update_task(t2, status="doing")
        self.assertEqual(self.svc.project_summary(self.p1)["doing"], 1)
        self.svc.update_task(t2, status="done")
        self.assertEqual(self.svc.project_summary(self.p1)["done"], 1)
        self.assertEqual(self.svc.workload(), [{"member": self.ann, "name": "Ann", "open": 1}])
        self.assertEqual([o["task"] for o in self.svc.overdue()], [t1])
        self.assertEqual(self.svc.label_counts(), [{"label": "bug", "count": 1}])

    def test_project_delete_and_member_removal(self):
        t1 = self.task(assignee=self.ann)
        self.assertEqual(self.svc.remove_member(self.ann), {"id": self.ann, "removed": True})
        self.assertIsNone(self.svc.get_task(t1)["assignee"])
        self.svc.delete_project(self.p1)
        with self.assertRaises(NotFound):
            self.svc.get_task(t1)
        self.assertEqual(self.svc.search("footer"), [])

    def test_outbox_audit_and_exports(self):
        t1 = self.task()
        events = self.svc.drain()
        self.assertEqual([e["type"] for e in events], ["project.created", "member.added", "label.added",
                                                       "task.created"])
        self.assertEqual(self.svc.drain(), [])
        self.assertEqual(self.svc.audit_log(1)[0]["action"], "task.create")
        self.assertEqual(self.svc.export_tasks_csv(self.p1).splitlines()[1], f"{t1},Fix the footer,todo,,,,2")
        self.assertEqual(len(self.svc.export_json()["tasks"]), 1)

    def test_rate_limit(self):
        for _ in range(ratelimit.RATE_LIMIT - 3):       # three calls were made in setUp
            self.svc.list_projects()
        with self.assertRaises(RateLimited):
            self.svc.list_projects()
        self.clock.advance(seconds=61)
        self.svc.list_projects()

    def test_snapshot_round_trip(self):
        t1 = self.task(assignee=self.ann, labels=["bug"])
        self.svc.add_comment(t1, self.ann, "hello world")
        copy = Lanes.load(self.svc.dump(), clock=self.clock)
        self.assertEqual(copy.get_task(t1), self.svc.get_task(t1))
        self.assertEqual(copy.search("hello")[0]["task"], t1)
        self.assertEqual(copy.create_project("Another")["id"], "p2")
        with self.assertRaises(Conflict):
            copy.add_member("Dup", "ann@example.com")


if __name__ == "__main__":
    unittest.main()

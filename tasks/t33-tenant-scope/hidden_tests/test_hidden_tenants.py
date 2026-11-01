"""Hidden tests for t33-tenant-scope. Test names carry the requirement number; see AUDIT.md."""
import json
import unittest
from datetime import datetime

from lanes import limits, ratelimit
from lanes.clock import FixedClock
from lanes.errors import Conflict, InvalidInput, NotFound, QuotaExceeded, RateLimited, UnknownTenant
from lanes.service import Lanes


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(datetime(2026, 3, 2, 9, 0))
        self.s = Lanes(clock=self.clock)
        self.s.create_tenant("acme", "Acme")
        self.s.create_tenant("globex", "Globex")

    def seed_acme(self):
        """p1 Website (t1 'Fix the footer', t2 'Footer links' done), p2 Blog (t3); u1 Ann, u2 Bob; bug, ui."""
        s = self.s
        s.create_project("acme", "Website")
        s.create_project("acme", "Blog")
        s.add_member("acme", "Ann", "ann@example.com")
        s.add_member("acme", "Bob", "bob@example.com")
        s.add_label("acme", "bug", "#ff0000")
        s.add_label("acme", "ui", "#00ff00")
        s.create_task("acme", "p1", "Fix the footer", assignee="u1", labels=["bug"], due="2026-03-01")
        s.create_task("acme", "p1", "Footer links", assignee="u2")
        s.create_task("acme", "p2", "Write a post", due="2026-02-01")
        s.update_task("acme", "t2", status="done")
        s.add_comment("acme", "t1", "u1", "Reproduced on Safari")
        s.add_comment("acme", "t3", "u2", "Draft is ready")

    def seed_globex(self):
        """p1 Billing (t1 'Refund bug'); u1 Zed; bug."""
        s = self.s
        s.create_project("globex", "Billing")
        s.add_member("globex", "Zed", "zed@example.com")
        s.add_label("globex", "bug")
        s.create_task("globex", "p1", "Refund bug", assignee="u1", labels=["bug"], due="2026-02-15")

    def seed(self):
        self.seed_acme()
        self.seed_globex()

    def assertNotFound(self, param, call, *args, **kw):
        with self.assertRaises(NotFound) as ctx:
            call(*args, **kw)
        self.assertEqual((ctx.exception.code, ctx.exception.param), ("not_found", param))


class TestTenants(Base):
    def test_r1_create_and_list(self):
        self.assertEqual(self.s.create_tenant("initech", "Initech"), {"id": "initech", "name": "Initech"})
        self.assertEqual(self.s.list_tenants(), {"data": [{"id": "acme", "name": "Acme"},
                                                          {"id": "globex", "name": "Globex"},
                                                          {"id": "initech", "name": "Initech"}]})

    def test_r1_bad_ids_and_duplicates(self):
        for bad in ("A", "x", "UPPER", "a" * 21, "bad_id", "has space", "", None, 7):
            with self.assertRaises(InvalidInput, msg=repr(bad)) as ctx:
                self.s.create_tenant(bad, "Name")
            self.assertEqual(ctx.exception.param, "tenant")
        with self.assertRaises(Conflict) as ctx:
            self.s.create_tenant("acme", "Again")
        self.assertEqual(ctx.exception.param, "tenant")
        self.assertEqual(len(self.s.list_tenants()["data"]), 2)

    def test_r1_every_method_checks_the_tenant(self):
        s, n = self.s, "nope"
        calls = [
            lambda: s.create_project(n, "x"), lambda: s.get_project(n, "p1"), lambda: s.list_projects(n),
            lambda: s.rename_project(n, "p1", "y"), lambda: s.archive_project(n, "p1"),
            lambda: s.delete_project(n, "p1"), lambda: s.add_member(n, "A", "a@example.com"),
            lambda: s.get_member(n, "u1"), lambda: s.list_members(n), lambda: s.remove_member(n, "u1"),
            lambda: s.add_label(n, "bug"), lambda: s.list_labels(n), lambda: s.tag_task(n, "t1", "bug"),
            lambda: s.untag_task(n, "t1", "bug"), lambda: s.create_task(n, "p1", "x"),
            lambda: s.get_task(n, "t1"), lambda: s.list_tasks(n), lambda: s.update_task(n, "t1", title="x"),
            lambda: s.assign_task(n, "t1", None), lambda: s.delete_task(n, "t1"),
            lambda: s.add_comment(n, "t1", "u1", "x"), lambda: s.list_comments(n, "t1"),
            lambda: s.search(n, "x"), lambda: s.project_summary(n, "p1"), lambda: s.workload(n),
            lambda: s.overdue(n), lambda: s.label_counts(n), lambda: s.export_tasks_csv(n, "p1"),
            lambda: s.export_json(n), lambda: s.drain(n), lambda: s.audit_log(n), lambda: s.delete_tenant(n),
        ]
        for number, call in enumerate(calls):
            with self.assertRaises(UnknownTenant, msg=number) as ctx:
                call()
            self.assertEqual((ctx.exception.code, ctx.exception.param), ("unknown_tenant", "tenant"))
        self.assertEqual(len(self.s.list_tenants()["data"]), 2)

    def test_r1_unknown_tenant_is_checked_before_anything_else(self):
        for _ in range(ratelimit.RATE_LIMIT + 50):
            with self.assertRaises(UnknownTenant):
                self.s.list_projects("nope")
        self.assertEqual(self.s.list_projects("acme"), {"data": []})
        with self.assertRaises(UnknownTenant):
            self.s.list_projects(None)

    def test_r5_tenant_admin_calls_do_not_count(self):
        for n in range(ratelimit.RATE_LIMIT + 20):
            self.s.create_tenant(f"t-{n}", "Many")
            self.s.list_tenants()
        self.assertEqual(self.s.list_projects("acme"), {"data": []})


class TestOwnIds(Base):
    def test_r2_sequences_are_per_tenant(self):
        self.seed()
        self.assertEqual([p["id"] for p in self.s.list_projects("acme")["data"]], ["p2", "p1"])
        self.assertEqual([p["id"] for p in self.s.list_projects("globex")["data"]], ["p1"])
        self.assertEqual(self.s.create_project("globex", "Second")["id"], "p2")
        self.assertEqual(self.s.create_project("acme", "Third")["id"], "p3")
        self.assertEqual(self.s.add_member("globex", "Yan", "yan@example.com")["id"], "u2")
        self.assertEqual(self.s.add_member("acme", "Cat", "cat@example.com")["id"], "u3")
        self.assertEqual(self.s.create_task("globex", "p1", "Another")["id"], "t2")
        self.assertEqual(self.s.create_task("acme", "p1", "Another")["id"], "t4")
        self.assertEqual(self.s.add_comment("globex", "t1", "u1", "hi")["id"], "c1")
        self.assertEqual(self.s.add_comment("acme", "t1", "u1", "hi")["id"], "c3")

    def test_r2_the_same_id_is_each_tenants_own_row(self):
        self.seed()
        self.assertEqual(self.s.get_project("acme", "p1")["name"], "Website")
        self.assertEqual(self.s.get_project("globex", "p1")["name"], "Billing")
        self.assertEqual(self.s.get_task("acme", "t1")["title"], "Fix the footer")
        self.assertEqual(self.s.get_task("globex", "t1")["title"], "Refund bug")
        self.assertEqual(self.s.get_member("acme", "u1")["name"], "Ann")
        self.assertEqual(self.s.get_member("globex", "u1")["name"], "Zed")
        self.assertEqual(self.s.list_comments("acme", "t1")["data"][0]["text"], "Reproduced on Safari")
        self.assertEqual(self.s.list_comments("globex", "t1")["data"], [])


class TestStrangers(Base):
    def test_r3_other_tenants_ids_are_not_found(self):
        self.seed()
        s = self.s
        before = s.export_json("acme")
        g_before = s.export_json("globex")
        cases = [
            ("project", lambda: s.get_project("globex", "p2")),
            ("project", lambda: s.rename_project("globex", "p2", "Hacked")),
            ("project", lambda: s.archive_project("globex", "p2")),
            ("project", lambda: s.delete_project("globex", "p2")),
            ("member", lambda: s.get_member("globex", "u2")),
            ("member", lambda: s.remove_member("globex", "u2")),
            ("project", lambda: s.create_task("globex", "p2", "Sneaky")),
            ("assignee", lambda: s.create_task("globex", "p1", "Sneaky", assignee="u2")),
            ("labels", lambda: s.create_task("globex", "p1", "Sneaky", labels=["ui"])),
            ("task", lambda: s.get_task("globex", "t3")),
            ("task", lambda: s.update_task("globex", "t3", title="Hacked")),
            ("assignee", lambda: s.assign_task("globex", "t1", "u2")),
            ("task", lambda: s.assign_task("globex", "t3", None)),
            ("task", lambda: s.delete_task("globex", "t3")),
            ("label", lambda: s.tag_task("globex", "t1", "ui")),
            ("task", lambda: s.tag_task("globex", "t3", "bug")),
            ("task", lambda: s.add_comment("globex", "t3", "u1", "Sneaky")),
            ("author", lambda: s.add_comment("globex", "t1", "u2", "Sneaky")),
            ("task", lambda: s.list_comments("globex", "t3")),
            ("project", lambda: s.list_tasks("globex", project="p2")),
            ("assignee", lambda: s.list_tasks("globex", assignee="u2")),
            ("label", lambda: s.list_tasks("globex", label="ui")),
            ("project", lambda: s.project_summary("globex", "p2")),
            ("project", lambda: s.export_tasks_csv("globex", "p2")),
        ]
        for param, call in cases:
            self.assertNotFound(param, call)
        self.assertEqual(s.export_json("acme"), before)
        self.assertEqual(s.export_json("globex"), g_before)

    def test_r3_a_shared_id_changes_only_the_callers_row(self):
        self.seed()
        s = self.s
        s.rename_project("globex", "p1", "Billing 2")
        s.update_task("globex", "t1", title="Refund bug fixed", status="done")
        s.assign_task("globex", "t1", None)
        s.tag_task("globex", "t1", "bug")
        s.add_comment("globex", "t1", "u1", "done")
        s.remove_member("globex", "u1")
        s.archive_project("globex", "p1")
        self.assertEqual(s.get_project("acme", "p1")["name"], "Website")
        self.assertFalse(s.get_project("acme", "p1")["archived"])
        t1 = s.get_task("acme", "t1")
        self.assertEqual((t1["title"], t1["status"], t1["assignee"], t1["comment_count"]),
                         ("Fix the footer", "todo", "u1", 1))
        self.assertEqual(s.get_member("acme", "u1")["name"], "Ann")
        self.assertEqual(s.create_task("acme", "p1", "Still open for new tasks")["project"], "p1")

    def test_r3_deleting_a_shared_id_leaves_the_other_tenant_alone(self):
        self.seed()
        s = self.s
        s.delete_task("globex", "t1")
        self.assertEqual(s.get_task("acme", "t1")["title"], "Fix the footer")
        s.delete_project("globex", "p1")
        self.assertEqual(s.get_project("acme", "p1")["task_count"], 2)
        self.assertEqual(s.list_comments("acme", "t1")["data"][0]["text"], "Reproduced on Safari")
        self.assertNotFound("task", s.get_task, "globex", "t1")


class TestNamesAndQuotas(Base):
    def test_r4_names_are_unique_per_tenant(self):
        s = self.s
        s.create_project("acme", "Website")
        s.add_member("acme", "Ann", "ann@example.com")
        s.add_label("acme", "bug")
        self.assertEqual(s.create_project("globex", "Website")["id"], "p1")
        self.assertEqual(s.add_member("globex", "Ann", "ANN@example.com")["email"], "ann@example.com")
        self.assertEqual(s.add_label("globex", "bug")["name"], "bug")
        for call, param in ((lambda: s.create_project("acme", "website"), "name"),
                            (lambda: s.add_member("acme", "Other", "Ann@Example.com"), "email"),
                            (lambda: s.add_label("acme", "BUG"), "name"),
                            (lambda: s.create_project("globex", "WEBSITE"), "name")):
            with self.assertRaises(Conflict) as ctx:
                call()
            self.assertEqual(ctx.exception.param, param)

    def test_r4_rename_into_another_tenants_name(self):
        s = self.s
        s.create_project("acme", "Website")
        s.create_project("globex", "Billing")
        s.create_project("globex", "Other")
        self.assertEqual(s.rename_project("globex", "p2", "Website")["name"], "Website")
        with self.assertRaises(Conflict):
            s.rename_project("globex", "p1", "website")

    def test_r4_project_quota_is_per_tenant(self):
        s = self.s
        for n in range(limits.MAX_PROJECTS):
            s.create_project("acme", f"A{n}")
        with self.assertRaises(QuotaExceeded) as ctx:
            s.create_project("acme", "one too many")
        self.assertEqual(ctx.exception.param, "projects")
        self.assertEqual(s.create_project("globex", "A0")["id"], "p1")
        s.delete_project("acme", "p1")
        self.assertEqual(s.create_project("acme", "fits again")["id"], f"p{limits.MAX_PROJECTS + 1}")

    def test_r4_task_quota_is_per_tenant_and_project(self):
        s = self.s
        s.create_project("acme", "A")
        s.create_project("globex", "G")
        for n in range(limits.MAX_TASKS_PER_PROJECT):
            s.create_task("acme", "p1", f"a{n}")
        with self.assertRaises(QuotaExceeded) as ctx:
            s.create_task("acme", "p1", "one too many")
        self.assertEqual(ctx.exception.param, "project")
        for n in range(limits.MAX_TASKS_PER_PROJECT):
            s.create_task("globex", "p1", f"g{n}")
        with self.assertRaises(QuotaExceeded):
            s.create_task("globex", "p1", "one too many")
        self.assertEqual(s.get_project("acme", "p1")["task_count"], limits.MAX_TASKS_PER_PROJECT)


class TestRateLimit(Base):
    def test_r5_each_tenant_has_its_own_window(self):
        for _ in range(ratelimit.RATE_LIMIT):
            self.s.list_projects("globex")
        for _ in range(ratelimit.RATE_LIMIT):
            self.s.list_projects("acme")
        for tenant in ("acme", "globex"):
            with self.assertRaises(RateLimited) as ctx:
                self.s.list_projects(tenant)
            self.assertEqual(ctx.exception.code, "rate_limited")
        self.s.create_tenant("initech", "Initech")
        self.assertEqual(self.s.list_projects("initech"), {"data": []})

    def test_r5_the_window_slides(self):
        for _ in range(ratelimit.RATE_LIMIT):
            self.s.list_projects("acme")
        with self.assertRaises(RateLimited):
            self.s.list_projects("acme")
        self.clock.advance(seconds=ratelimit.WINDOW_SECONDS - 1)
        with self.assertRaises(RateLimited):
            self.s.list_projects("acme")
        self.clock.advance(seconds=2)
        self.assertEqual(self.s.list_projects("acme"), {"data": []})

    def test_r5_a_blocked_tenant_does_not_block_others_calls_by_id(self):
        for _ in range(ratelimit.RATE_LIMIT):
            self.s.list_projects("acme")
        self.s.create_project("globex", "Billing")
        self.assertEqual(self.s.get_project("globex", "p1")["name"], "Billing")


class TestSharedCaches(Base):
    def test_r6_task_cache_is_per_tenant(self):
        self.seed()
        s = self.s
        self.assertEqual(s.get_task("acme", "t1")["title"], "Fix the footer")
        self.assertEqual(s.get_task("globex", "t1")["title"], "Refund bug")          # not acme's cached view
        self.assertEqual(s.get_task("acme", "t1")["title"], "Fix the footer")
        s.update_task("acme", "t1", title="Fix the header")
        self.assertEqual(s.get_task("acme", "t1")["title"], "Fix the header")
        self.assertEqual(s.get_task("globex", "t1")["title"], "Refund bug")
        s.tag_task("globex", "t1", "bug")
        s.update_task("globex", "t1", status="doing")
        self.assertEqual(s.get_task("globex", "t1")["status"], "doing")
        self.assertEqual(s.get_task("acme", "t1")["status"], "todo")

    def test_r6_writes_refresh_only_their_own_cached_view(self):
        self.seed()
        s = self.s
        s.get_task("acme", "t1")
        s.get_task("globex", "t1")
        s.add_comment("acme", "t1", "u1", "another one")
        s.assign_task("acme", "t1", "u2")
        self.assertEqual(s.get_task("acme", "t1")["comment_count"], 2)
        self.assertEqual(s.get_task("acme", "t1")["assignee"], "u2")
        self.assertEqual(s.get_task("globex", "t1")["comment_count"], 0)
        self.assertEqual(s.get_task("globex", "t1")["assignee"], "u1")
        s.remove_member("acme", "u2")
        self.assertIsNone(s.get_task("acme", "t1")["assignee"])
        self.assertEqual(s.get_task("globex", "t1")["assignee"], "u1")

    def test_r6_deletes_in_one_tenant_keep_the_other_tenants_cache_valid(self):
        self.seed()
        s = self.s
        s.get_task("acme", "t1")
        s.get_task("globex", "t1")
        s.delete_task("globex", "t1")
        self.assertNotFound("task", s.get_task, "globex", "t1")
        self.assertEqual(s.get_task("acme", "t1")["title"], "Fix the footer")
        s.get_task("acme", "t3")
        s.delete_project("acme", "p2")
        self.assertNotFound("task", s.get_task, "acme", "t3")

    def test_r6_search_is_per_tenant(self):
        self.seed()
        s = self.s
        s.update_task("globex", "t1", title="Footer refund bug")
        self.assertEqual([(h["task"], h["score"]) for h in s.search("acme", "footer")], [("t1", 2), ("t2", 2)])
        self.assertEqual([(h["task"], h["score"], h["title"]) for h in s.search("globex", "footer")],
                         [("t1", 2, "Footer refund bug")])
        self.assertEqual(s.search("globex", "safari"), [])
        self.assertEqual(s.search("acme", "refund"), [])

    def test_r6_search_entries_survive_the_other_tenants_deletes_and_edits(self):
        self.seed()
        s = self.s
        s.update_task("globex", "t1", title="Footer refund bug")
        s.delete_task("acme", "t1")
        self.assertEqual([h["task"] for h in s.search("globex", "footer")], ["t1"])
        s.add_comment("acme", "t2", "u1", "footer footer")
        s.update_task("acme", "t2", title="Something else")
        self.assertEqual([(h["task"], h["score"]) for h in s.search("globex", "footer")], [("t1", 2)])
        s.delete_project("acme", "p1")
        self.assertEqual([h["task"] for h in s.search("globex", "refund")], ["t1"])
        s.add_comment("globex", "t1", "u1", "refund again")
        self.assertEqual(s.search("globex", "refund")[0]["score"], 3)
        self.assertEqual(s.search("acme", "refund"), [])

    def test_r6_summaries_are_per_tenant(self):
        self.seed()
        s = self.s
        first = s.project_summary("acme", "p1")
        self.assertEqual((first["name"], first["tasks"], first["todo"], first["done"]), ("Website", 2, 1, 1))
        other = s.project_summary("globex", "p1")
        self.assertEqual((other["name"], other["tasks"], other["todo"], other["done"]), ("Billing", 1, 1, 0))
        s.create_task("globex", "p1", "Second")
        self.assertEqual(s.project_summary("globex", "p1")["tasks"], 2)
        self.assertEqual(s.project_summary("acme", "p1"), first)
        s.update_task("acme", "t1", status="done")
        self.assertEqual(s.project_summary("acme", "p1")["done"], 2)
        self.assertEqual(s.project_summary("globex", "p1")["done"], 0)
        s.delete_project("globex", "p1")
        self.assertEqual(s.project_summary("acme", "p1")["tasks"], 2)

    def test_r6_member_removal_in_one_tenant_only(self):
        self.seed()
        s = self.s
        s.remove_member("acme", "u1")
        self.assertIsNone(s.get_task("acme", "t1")["assignee"])
        self.assertEqual(s.get_task("globex", "t1")["assignee"], "u1")
        self.assertEqual(s.workload("globex"), [{"member": "u1", "name": "Zed", "open": 1}])
        self.assertEqual([e["data"] for e in s.drain("acme") if e["type"] == "member.removed"],
                         [{"id": "u1", "unassigned": 1}])


class TestEvents(Base):
    def test_r7_drain_is_per_tenant(self):
        self.seed()
        acme = self.s.drain("acme")
        self.assertEqual({e["tenant"] for e in acme}, {"acme"})
        self.assertEqual([e["seq"] for e in acme], list(range(1, len(acme) + 1)))
        self.assertEqual([e["type"] for e in acme][:3], ["project.created", "project.created", "member.added"])
        self.assertEqual(self.s.drain("acme"), [])
        globex = self.s.drain("globex")
        self.assertEqual([e["type"] for e in globex], ["project.created", "member.added", "label.added",
                                                       "task.created"])
        self.assertEqual({e["tenant"] for e in globex}, {"globex"})
        self.assertEqual([e["seq"] for e in globex], [1, 2, 3, 4])
        self.assertEqual(self.s.drain("globex"), [])

    def test_r7_seq_continues_after_a_drain(self):
        self.seed_globex()
        self.s.drain("globex")
        self.s.create_task("globex", "p1", "Next")
        self.assertEqual([(e["seq"], e["type"]) for e in self.s.drain("globex")], [(5, "task.created")])

    def test_r7_drain_leaves_other_tenants_events_in_place(self):
        self.seed()
        self.s.drain("acme")
        self.s.create_task("acme", "p1", "New")
        self.assertEqual(len(self.s.drain("globex")), 4)
        self.assertEqual([e["data"] for e in self.s.drain("acme")], [{"id": "t4", "project": "p1"}])

    def test_r7_subscribers_see_every_tenant(self):
        seen = []
        self.s.subscribe(seen.append)
        self.s.create_project("acme", "Website")
        self.s.create_project("globex", "Billing")
        self.s.add_member("acme", "Ann", "ann@example.com")
        self.assertEqual([(e["tenant"], e["seq"], e["type"]) for e in seen],
                         [("acme", 1, "project.created"), ("globex", 1, "project.created"),
                          ("acme", 2, "member.added")])
        self.assertEqual(len(self.s.drain("acme")), 2)

    def test_r7_audit_is_per_tenant(self):
        self.seed()
        entries = self.s.audit_log("globex", 20)
        self.assertEqual([(e["seq"], e["action"], e["target"]) for e in reversed(entries)],
                         [(1, "project.create", "p1"), (2, "member.add", "u1"), (3, "label.add", "bug"),
                          (4, "task.create", "t1")])
        acme = self.s.audit_log("acme", 100)
        self.assertEqual(acme[0]["seq"], len(acme))
        self.assertNotIn("Refund bug", [e["detail"] for e in acme])
        self.assertEqual(len(self.s.audit_log("acme", 3)), 3)
        self.assertEqual(self.s.audit_log("acme", 1)[0]["seq"], len(acme))


class TestReports(Base):
    def test_r8_workload_overdue_and_labels(self):
        self.seed()
        s = self.s
        self.assertEqual(s.workload("acme"), [{"member": "u1", "name": "Ann", "open": 1},
                                              {"member": "u2", "name": "Bob", "open": 0}])
        self.assertEqual(s.workload("globex"), [{"member": "u1", "name": "Zed", "open": 1}])
        self.assertEqual([o["task"] for o in s.overdue("acme")], ["t3", "t1"])
        self.assertEqual([(o["task"], o["title"]) for o in s.overdue("globex")], [("t1", "Refund bug")])
        self.assertEqual(s.label_counts("acme"), [{"label": "bug", "count": 1}])
        s.tag_task("globex", "t1", "bug")
        self.assertEqual(s.label_counts("globex"), [{"label": "bug", "count": 1}])
        self.assertEqual(s.list_labels("acme")["data"], [{"name": "bug", "color": "#ff0000"},
                                                         {"name": "ui", "color": "#00ff00"}])
        self.assertEqual(s.list_labels("globex")["data"], [{"name": "bug", "color": "#888888"}])

    def test_r8_lists_and_filters(self):
        self.seed()
        s = self.s
        self.assertEqual([t["id"] for t in s.list_tasks("acme")["data"]], ["t1", "t2", "t3"])
        self.assertEqual([t["title"] for t in s.list_tasks("globex")["data"]], ["Refund bug"])
        self.assertEqual([t["id"] for t in s.list_tasks("acme", label="bug")["data"]], ["t1"])
        self.assertEqual([t["id"] for t in s.list_tasks("globex", assignee="u1")["data"]], ["t1"])
        self.assertEqual([m["name"] for m in s.list_members("globex")["data"]], ["Zed"])
        self.assertEqual([p["name"] for p in s.list_projects("acme")["data"]], ["Blog", "Website"])
        self.assertEqual(len(s.list_comments("acme", "t1")["data"]), 1)

    def test_r8_exports(self):
        self.seed()
        s = self.s
        lines = s.export_tasks_csv("acme", "p1").splitlines()
        self.assertEqual(lines[0], "id,title,status,assignee,labels,due,priority")
        self.assertEqual(lines[1:], ["t1,Fix the footer,todo,u1,bug,2026-03-01,2", "t2,Footer links,done,u2,,,2"])
        self.assertEqual(s.export_tasks_csv("globex", "p1").splitlines()[1:], ["t1,Refund bug,todo,u1,bug,2026-02-15,2"])
        everything = s.export_json("globex")
        self.assertEqual([p["name"] for p in everything["projects"]], ["Billing"])
        self.assertEqual([m["name"] for m in everything["members"]], ["Zed"])
        self.assertEqual([t["title"] for t in everything["tasks"]], ["Refund bug"])
        self.assertEqual(len(s.export_json("acme")["tasks"]), 3)


class TestRemovingTenants(Base):
    def test_r9_delete_and_recreate(self):
        self.seed()
        s = self.s
        s.get_task("acme", "t1")
        s.project_summary("acme", "p1")
        self.assertEqual(s.delete_tenant("acme"), {"id": "acme", "deleted": True})
        self.assertEqual(s.list_tenants()["data"], [{"id": "globex", "name": "Globex"}])
        with self.assertRaises(UnknownTenant):
            s.get_task("acme", "t1")
        with self.assertRaises(UnknownTenant):
            s.delete_tenant("acme")
        self.assertEqual(s.create_tenant("acme", "Acme again"), {"id": "acme", "name": "Acme again"})
        self.assertEqual(s.list_projects("acme"), {"data": []})
        self.assertEqual(s.list_members("acme"), {"data": []})
        self.assertEqual(s.list_labels("acme"), {"data": []})
        self.assertNotFound("task", s.get_task, "acme", "t1")
        self.assertNotFound("project", s.project_summary, "acme", "p1")
        self.assertEqual(s.search("acme", "footer"), [])
        self.assertEqual(s.drain("acme"), [])
        self.assertEqual(s.audit_log("acme"), [])
        self.assertEqual(s.create_project("acme", "Fresh")["id"], "p1")
        self.assertEqual(s.create_task("acme", "p1", "Brand new", labels=[]).get("id"), "t1")
        self.assertEqual(s.get_task("acme", "t1")["title"], "Brand new")
        self.assertEqual(s.project_summary("acme", "p1")["tasks"], 1)
        self.assertEqual([h["title"] for h in s.search("acme", "brand")], ["Brand new"])

    def test_r9_other_tenants_are_untouched(self):
        self.seed()
        s = self.s
        s.get_task("globex", "t1")
        s.project_summary("globex", "p1")
        s.delete_tenant("acme")
        self.assertEqual(s.get_task("globex", "t1")["title"], "Refund bug")
        self.assertEqual(s.project_summary("globex", "p1")["name"], "Billing")
        self.assertEqual([h["task"] for h in s.search("globex", "refund")], ["t1"])
        self.assertEqual(len(s.drain("globex")), 4)
        self.assertEqual(s.audit_log("globex")[0]["seq"], 4)
        self.assertEqual(s.create_task("globex", "p1", "Next")["id"], "t2")

    def test_r9_the_rate_limit_window_goes_with_the_tenant(self):
        for _ in range(ratelimit.RATE_LIMIT):
            self.s.list_projects("acme")
        with self.assertRaises(RateLimited):
            self.s.list_projects("acme")
        self.s.delete_tenant("acme")
        self.s.create_tenant("acme", "Acme")
        self.assertEqual(self.s.list_projects("acme"), {"data": []})


class TestSnapshot(Base):
    def test_r10_round_trip(self):
        self.seed()
        s = self.s
        s.drain("acme")
        data = json.loads(json.dumps(s.dump()))
        copy = Lanes.load(data, clock=self.clock)
        self.assertEqual(copy.list_tenants(), s.list_tenants())
        for tenant in ("acme", "globex"):
            self.assertEqual(copy.export_json(tenant), s.export_json(tenant))
            self.assertEqual(copy.audit_log(tenant, 100), s.audit_log(tenant, 100))
        self.assertEqual(copy.get_task("acme", "t1")["title"], "Fix the footer")
        self.assertEqual(copy.get_task("globex", "t1")["title"], "Refund bug")
        self.assertEqual([h["task"] for h in copy.search("acme", "footer")], ["t1", "t2"])
        self.assertEqual([h["task"] for h in copy.search("globex", "refund")], ["t1"])
        self.assertEqual(copy.search("globex", "footer"), [])
        self.assertEqual(copy.search("acme", "safari")[0]["task"], "t1")
        self.assertEqual(copy.create_project("acme", "Third")["id"], "p3")
        self.assertEqual(copy.create_project("globex", "Second")["id"], "p2")
        self.assertEqual(copy.create_task("globex", "p1", "Next")["id"], "t2")
        self.assertEqual(copy.create_task("acme", "p1", "Next")["id"], "t4")

    def test_r10_loaded_tenants_stay_isolated(self):
        self.seed()
        copy = Lanes.load(self.s.dump(), clock=self.clock)
        copy.delete_task("globex", "t1")
        self.assertEqual(copy.get_task("acme", "t1")["title"], "Fix the footer")
        self.assertEqual([h["task"] for h in copy.search("acme", "footer")], ["t1", "t2"])
        self.assertNotFound("task", copy.get_task, "globex", "t1")
        self.assertEqual(copy.drain("acme"), [])

    def test_r10_older_dump_becomes_the_default_tenant(self):
        old = {"version": 1, "ids": {"p": 1, "u": 1, "t": 1, "c": 1},
               "projects": [{"id": "p1", "name": "Website", "archived": False, "created_at": "2026-03-01T09:00:00Z"}],
               "members": [{"id": "u1", "name": "Ann", "email": "ann@example.com"}],
               "labels": [{"name": "bug", "color": "#ff0000"}],
               "tasks": [{"id": "t1", "project": "p1", "title": "Fix the footer", "status": "todo",
                          "assignee": "u1", "labels": ["bug"], "due": None, "priority": 2,
                          "created_at": "2026-03-01T09:00:00Z", "updated_at": "2026-03-01T09:00:00Z"}],
               "comments": [{"id": "c1", "task": "t1", "author": "u1", "text": "Safari only",
                             "created_at": "2026-03-01T09:00:00Z"}],
               "audit": [{"seq": 1, "at": "2026-03-01T09:00:00Z", "action": "project.create", "target": "p1",
                          "detail": "Website"}]}
        copy = Lanes.load(old, clock=self.clock)
        self.assertEqual(copy.list_tenants(), {"data": [{"id": "default", "name": "Default"}]})
        self.assertEqual(copy.get_task("default", "t1")["comment_count"], 1)
        self.assertEqual(copy.search("default", "safari")[0]["task"], "t1")
        self.assertEqual(copy.audit_log("default")[0]["action"], "project.create")
        self.assertEqual(copy.create_task("default", "p1", "Next")["id"], "t2")
        with self.assertRaises(UnknownTenant):
            copy.list_projects("acme")


if __name__ == "__main__":
    unittest.main()

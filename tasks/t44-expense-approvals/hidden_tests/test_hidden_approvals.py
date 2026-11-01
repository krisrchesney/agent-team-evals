"""Hidden tests for t44-expense-approvals. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from spendflow import Service
from spendflow.clock import FixedClock
from spendflow.errors import Conflict, InvalidRequest, NotFound, SpendError

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()                              # 2026-01-05T09:00:00Z
        self.svc = Service(clock=self.clock)
        self.dana = self.svc.call("employee.create", name="Dana")["id"]                    # top, no manager
        self.max = self.svc.call("employee.create", name="Max", manager=self.dana)["id"]
        self.eve = self.svc.call("employee.create", name="Eve", manager=self.max)["id"]
        self.sam = self.svc.call("employee.create", name="Sam", manager=self.max)["id"]
        self.svc.bus.log.clear()

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def draft(self, employee=None, amount=1850, date="2026-01-02", description="Train ticket"):
        return self.call("expense.create", employee=employee or self.eve, amount=amount, date=date,
                         description=description)["id"]

    def submitted(self, **kw):
        e = self.draft(**kw)
        self.call("expense.submit", expense=e)
        self.svc.bus.log.clear()
        return e

    def approve(self, expense, by):
        return self.call("expense.approve", expense=expense, by=by)

    def reject(self, expense, by, reason="Not a business cost"):
        return self.call("expense.reject", expense=expense, by=by, reason=reason)

    def get(self, expense):
        return self.call("expense.retrieve", expense=expense)

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, SpendError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestSubmit(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"expense.submit", "expense.approve", "expense.reject"} <= ops)
        self.assertTrue({"expense.create", "employee.create"} <= ops)

    def test_submit(self):
        e = self.draft()
        self.clock.advance(hours=2)
        self.svc.bus.log.clear()
        out = self.call("expense.submit", expense=e)
        self.assertEqual((out["status"], out["version"], out["updated_at"]), ("submitted", 2, "2026-01-05T11:00:00Z"))
        self.assertEqual((out["employee"], out["amount"], out["date"]), (self.eve, 1850, "2026-01-02"))
        self.assertEqual(self.svc.bus.log, [{"type": "expense.submitted", "data": {"expense": out}}])
        self.assertEqual(self.get(e), out)

    def test_unknown_and_missing_expense(self):
        for op, extra in (("expense.submit", {}), ("expense.approve", {"by": self.max}),
                          ("expense.reject", {"by": self.max, "reason": "no"})):
            with self.subTest(op=op):
                self.assertError(NotFound, "expense", op, expense="expense_9999", **extra)
                self.assertError(InvalidRequest, "expense", op, **extra)

    def test_approve_and_reject_need_a_known_by(self):
        e = self.submitted()
        self.assertError(NotFound, "by", "expense.approve", expense=e, by="employee_9999")
        self.assertError(InvalidRequest, "by", "expense.approve", expense=e)
        self.assertError(NotFound, "by", "expense.reject", expense=e, by="employee_9999", reason="no")
        self.assertError(InvalidRequest, "by", "expense.reject", expense=e, reason="no")

    def test_failures_change_nothing(self):
        e = self.draft()
        self.svc.bus.log.clear()
        with self.assertRaises(SpendError):
            self.call("expense.submit", expense="expense_9999")
        self.assertEqual((self.svc.bus.log, self.get(e)["version"]), ([], 1))


class TestWho(Base):
    """answers.json: who"""

    def test_the_manager_approves(self):
        e = self.submitted()
        out = self.approve(e, self.max)
        self.assertEqual((out["status"], out["version"]), ("approved", 3))
        self.assertEqual(self.svc.bus.log, [{"type": "expense.approved", "data": {"expense": out}}])

    def test_the_manager_rejects(self):
        e = self.submitted()
        out = self.reject(e, self.max)
        self.assertEqual((out["status"], out["version"]), ("rejected", 3))
        self.assertEqual(self.svc.bus.log, [{"type": "expense.rejected", "data": {"expense": out}}])

    def test_nobody_else_can_decide(self):
        e = self.submitted()
        for who in (self.sam, self.dana, self.eve):
            with self.subTest(who=who):
                self.assertError(Conflict, "by", "expense.approve", expense=e, by=who)
                self.assertError(Conflict, "by", "expense.reject", expense=e, by=who, reason="no")
        self.assertEqual((self.get(e)["status"], self.get(e)["version"], self.svc.bus.log), ("submitted", 2, []))

    def test_the_manager_of_one_employee_is_not_the_manager_of_all(self):
        other = self.svc.call("employee.create", name="Ola", manager=self.dana)["id"]
        e = self.submitted(employee=other)
        self.assertError(Conflict, "by", "expense.approve", expense=e, by=self.max)
        self.assertEqual(self.approve(e, self.dana)["status"], "approved")

    def test_no_manager_means_no_submitting(self):
        e = self.draft(employee=self.dana)
        self.assertError(Conflict, "expense", "expense.submit", expense=e)
        self.assertEqual((self.get(e)["status"], self.svc.bus.log[-1]["type"]), ("draft", "expense.created"))

    def test_only_a_submitted_expense_can_be_decided(self):
        draft = self.draft()
        done = self.submitted(date="2026-01-03")
        self.approve(done, self.max)
        gone = self.submitted(date="2026-01-04")
        self.reject(gone, self.max)
        for e in (draft, done, gone):
            with self.subTest(expense=e):
                self.assertError(Conflict, "expense", "expense.approve", expense=e, by=self.max)
                self.assertError(Conflict, "expense", "expense.reject", expense=e, by=self.max, reason="no")


class TestSecond(Base):
    """answers.json: second"""

    def test_big_expense_needs_two_approvals(self):
        e = self.submitted(amount=50000)
        first = self.approve(e, self.max)
        self.assertEqual((first["status"], first["approvals"]), ("submitted", [self.max]))
        self.assertEqual(self.svc.bus.log, [{"type": "expense.approved", "data": {"expense": first}}])
        second = self.approve(e, self.dana)
        self.assertEqual((second["status"], second["approvals"], second["version"]), ("approved", [self.max, self.dana], 4))

    def test_just_under_the_threshold_needs_one(self):
        e = self.submitted(amount=49999)
        out = self.approve(e, self.max)
        self.assertEqual((out["status"], out["approvals"]), ("approved", [self.max]))

    def test_the_skip_level_cannot_go_first(self):
        e = self.submitted(amount=60000)
        self.assertError(Conflict, "by", "expense.approve", expense=e, by=self.dana)
        self.assertEqual((self.get(e)["approvals"], self.get(e)["version"]), ([], 2))

    def test_the_manager_cannot_approve_twice(self):
        e = self.submitted(amount=60000)
        self.approve(e, self.max)
        self.assertError(Conflict, "by", "expense.approve", expense=e, by=self.max)
        self.assertEqual(self.get(e)["approvals"], [self.max])

    def test_nobody_else_is_next(self):
        e = self.submitted(amount=60000)
        self.approve(e, self.max)
        for who in (self.sam, self.eve):
            with self.subTest(who=who):
                self.assertError(Conflict, "by", "expense.approve", expense=e, by=who)

    def test_a_manager_at_the_top_is_enough(self):
        e = self.submitted(employee=self.max, amount=90000)
        out = self.approve(e, self.dana)
        self.assertEqual((out["status"], out["approvals"]), ("approved", [self.dana]))

    def test_the_first_approver_can_reject(self):
        e = self.submitted(amount=60000)
        self.assertEqual(self.reject(e, self.max)["status"], "rejected")

    def test_only_the_next_approver_can_reject(self):
        e = self.submitted(amount=60000)
        self.assertError(Conflict, "by", "expense.reject", expense=e, by=self.dana, reason="no")
        self.approve(e, self.max)
        self.assertError(Conflict, "by", "expense.reject", expense=e, by=self.max, reason="no")
        self.assertEqual(self.reject(e, self.dana)["status"], "rejected")

    def test_approvals_start_empty_and_cannot_continue_after_the_end(self):
        e = self.submitted(amount=60000)
        self.assertEqual(self.get(e)["approvals"], [])
        self.approve(e, self.max)
        self.approve(e, self.dana)
        self.assertError(Conflict, "expense", "expense.approve", expense=e, by=self.dana)


class TestWindow(Base):
    """answers.json: window"""

    def test_day_30_is_fine(self):
        e = self.draft(date="2025-12-06")
        self.assertEqual(self.call("expense.submit", expense=e)["status"], "submitted")

    def test_day_31_is_refused(self):
        e = self.draft(date="2025-12-05")
        self.assertError(Conflict, "expense", "expense.submit", expense=e)
        self.assertEqual((self.get(e)["status"], self.get(e)["version"]), ("draft", 1))
        self.assertEqual(self.svc.bus.log[-1]["type"], "expense.created")

    def test_days_are_calendar_days(self):
        e = self.draft(date="2025-12-06")
        self.clock.advance(hours=14, minutes=59, seconds=59)           # 2026-01-05T23:59:59Z, still day 30
        self.assertEqual(self.call("expense.submit", expense=e)["status"], "submitted")
        late = self.draft(date="2025-12-06", amount=99)
        self.clock.advance(seconds=1)                                  # 2026-01-06T00:00:00Z, day 31
        self.assertError(Conflict, "expense", "expense.submit", expense=late)

    def test_a_future_date_is_fine(self):
        e = self.draft(date="2026-02-01")
        self.assertEqual(self.call("expense.submit", expense=e)["status"], "submitted")

    def test_not_checked_again_after_submitting(self):
        e = self.submitted(date="2025-12-06")
        self.clock.advance(days=20)
        self.assertEqual(self.approve(e, self.max)["status"], "approved")


class TestDuplicate(Base):
    """answers.json: duplicate"""

    def test_same_amount_and_date_as_a_submitted_expense(self):
        self.submitted(description="Taxi")
        other = self.draft(description="Cab home")
        self.assertError(Conflict, "expense", "expense.submit", expense=other)
        self.assertEqual(self.get(other)["status"], "draft")

    def test_still_a_duplicate_once_approved(self):
        first = self.submitted()
        self.approve(first, self.max)
        other = self.draft(description="Again")
        self.assertError(Conflict, "expense", "expense.submit", expense=other)

    def test_different_amount_date_or_employee_is_fine(self):
        self.submitted()
        for kw in ({"amount": 1851}, {"date": "2026-01-03"}, {"employee": self.sam}):
            with self.subTest(**kw):
                e = self.draft(**kw)
                self.assertEqual(self.call("expense.submit", expense=e)["status"], "submitted")

    def test_drafts_do_not_count(self):
        a = self.draft()
        b = self.draft(description="Second")
        self.assertEqual(self.call("expense.submit", expense=b)["status"], "submitted")
        self.assertError(Conflict, "expense", "expense.submit", expense=a)

    def test_a_rejected_expense_does_not_count(self):
        first = self.submitted()
        self.reject(first, self.max)
        again = self.draft(description="Fixed receipt")
        self.assertEqual(self.call("expense.submit", expense=again)["status"], "submitted")

    def test_only_drafts_can_be_submitted(self):
        first = self.submitted()
        self.assertError(Conflict, "expense", "expense.submit", expense=first)
        self.reject(first, self.max)
        self.assertError(Conflict, "expense", "expense.submit", expense=first)
        self.assertEqual(self.get(first)["status"], "rejected")


class TestReason(Base):
    """answers.json: reason"""

    def test_reject_needs_a_reason(self):
        e = self.submitted()
        for reason in (None, "", "   ", 5):
            with self.subTest(reason=reason):
                self.assertError(InvalidRequest, "reason", "expense.reject", expense=e, by=self.max, reason=reason)
        self.assertError(InvalidRequest, "reason", "expense.reject", expense=e, by=self.max)
        self.assertEqual((self.get(e)["status"], self.svc.bus.log), ("submitted", []))

    def test_the_reason_is_shown(self):
        e = self.draft()
        self.assertIsNone(self.get(e)["reason"])
        self.call("expense.submit", expense=e)
        self.assertIsNone(self.get(e)["reason"])
        out = self.reject(e, self.max, reason="Personal purchase")
        self.assertEqual((out["reason"], out["status"]), ("Personal purchase", "rejected"))
        self.assertEqual(self.get(e)["reason"], "Personal purchase")

    def test_an_approved_expense_has_no_reason(self):
        e = self.submitted()
        self.assertIsNone(self.approve(e, self.max)["reason"])


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        e = self.draft()
        out = self.get(e)
        self.assertEqual((out["id"], out["status"], out["version"], out["amount"]), ("expense_0001", "draft", 1, 1850))
        self.assertEqual(self.call("employee.retrieve", employee=self.eve)["manager"], self.max)
        self.assertEqual([x["id"] for x in self.call("expense.list", employee=self.eve)["data"]], [e])
        self.assertError(InvalidRequest, "date", "expense.create", employee=self.eve, amount=1, date="x", description="d")


if __name__ == "__main__":
    unittest.main()

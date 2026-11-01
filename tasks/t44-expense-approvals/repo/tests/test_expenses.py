import unittest

from spendflow import Service
from spendflow.clock import FixedClock
from spendflow.errors import InvalidRequest, NotFound


class ExpensesTest(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.dana = self.svc.call("employee.create", name="Dana")["id"]
        self.eve = self.svc.call("employee.create", name="Eve", manager=self.dana)["id"]

    def expense(self, **kw):
        args = dict(employee=self.eve, amount=1850, date="2026-01-02", description="Train ticket")
        args.update(kw)
        return self.svc.call("expense.create", **args)

    def test_employee_manager(self):
        self.assertIsNone(self.svc.call("employee.retrieve", employee=self.dana)["manager"])
        self.assertEqual(self.svc.call("employee.retrieve", employee=self.eve)["manager"], self.dana)

    def test_unknown_manager(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("employee.create", name="Sam", manager="employee_9999")
        self.assertEqual(ctx.exception.param, "manager")

    def test_expense_view(self):
        e = self.expense()
        self.assertEqual((e["id"], e["employee"], e["amount"], e["date"], e["status"], e["version"]),
                         ("expense_0001", self.eve, 1850, "2026-01-02", "draft", 1))

    def test_bad_input(self):
        for kw, param in (({"amount": 0}, "amount"), ({"amount": 9.5}, "amount"), ({"date": "02/01/2026"}, "date"),
                          ({"date": "2026-02-30"}, "date"), ({"description": " "}, "description")):
            with self.subTest(**kw):
                with self.assertRaises(InvalidRequest) as ctx:
                    self.expense(**kw)
                self.assertEqual(ctx.exception.param, param)

    def test_list_in_date_order(self):
        self.expense(date="2026-01-04")
        self.expense(date="2026-01-01")
        rows = self.svc.call("expense.list", employee=self.eve)["data"]
        self.assertEqual([r["date"] for r in rows], ["2026-01-01", "2026-01-04"])

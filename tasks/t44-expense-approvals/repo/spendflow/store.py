from .errors import NotFound


class Store:
    def __init__(self):
        self.employees = {}
        self.expenses = {}

    def get_employee(self, employee_id, param="employee"):
        employee = self.employees.get(employee_id)
        if employee is None:
            raise NotFound(f"no employee {employee_id!r}", param=param)
        return employee

    def get_expense(self, expense_id):
        expense = self.expenses.get(expense_id)
        if expense is None:
            raise NotFound(f"no expense {expense_id!r}", param="expense")
        return expense

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def expenses_of(self, employee_id):
        return sorted((e for e in self.expenses.values() if e.employee == employee_id), key=lambda e: (e.date, e.id))

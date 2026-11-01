from .. import validate
from ..models import Expense
from ..views import expense_view
from .registry import operation


@operation("expense.create")
def create(svc, params):
    now = svc.clock.now()
    employee = svc.store.get_employee(validate.require_str(params, "employee"))
    amount = validate.cents(params, "amount")
    date = validate.require_date(params, "date")
    description = validate.require_str(params, "description")
    expense = Expense(id=svc.ids.new("expense"), employee=employee.id, amount=amount, date=date,
                      description=description, status="draft", created_at=now, updated_at=now)
    svc.store.expenses[expense.id] = expense
    view = expense_view(expense)
    svc.bus.emit("expense.created", {"expense": view})
    return view


@operation("expense.retrieve")
def retrieve(svc, params):
    return expense_view(svc.store.get_expense(validate.require_str(params, "expense")))


@operation("expense.list")
def list_expenses(svc, params):
    limit = validate.limit(params)
    if params.get("employee") is not None:
        employee = svc.store.get_employee(validate.require_str(params, "employee"))
        rows = svc.store.expenses_of(employee.id)
    else:
        rows = sorted(svc.store.expenses.values(), key=lambda e: (e.date, e.id))
    return {"data": [expense_view(e) for e in rows[:limit]], "has_more": len(rows) > limit}

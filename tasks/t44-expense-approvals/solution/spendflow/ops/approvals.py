from .. import validate
from ..errors import Conflict
from ..views import expense_view
from .registry import operation

WINDOW_DAYS = 30
SECOND_APPROVAL_FROM = 50000    # cents


def _needs_two(svc, expense):
    manager = svc.store.get_employee(expense.employee).manager
    return (expense.amount >= SECOND_APPROVAL_FROM and manager is not None
            and svc.store.get_employee(manager).manager is not None)


def _next_approver(svc, expense):
    """Who must act next: the manager first, then (for a big expense) the manager's manager."""
    manager = svc.store.get_employee(svc.store.get_employee(expense.employee).manager)
    return manager.id if not expense.approvals else manager.manager


def _decide(svc, params):
    """Shared start of approve and reject: returns (now, expense) once `by` is the one whose turn it is."""
    now = svc.clock.now()
    expense = svc.store.get_expense(validate.require_str(params, "expense"))
    by = svc.store.get_employee(validate.require_str(params, "by"), param="by")
    return now, expense, by


@operation("expense.submit")
def submit(svc, params):
    now = svc.clock.now()
    expense = svc.store.get_expense(validate.require_str(params, "expense"))
    if expense.status != "draft":
        raise Conflict(f"expense {expense.id} is {expense.status}", param="expense")
    if svc.store.get_employee(expense.employee).manager is None:
        raise Conflict("this employee has no manager to approve expenses", param="expense")
    if (now.date() - expense.date).days > WINDOW_DAYS:
        raise Conflict(f"expenses must be submitted within {WINDOW_DAYS} days", param="expense")
    for other in svc.store.expenses_of(expense.employee):
        if (other.id != expense.id and other.status in ("submitted", "approved")
                and other.amount == expense.amount and other.date == expense.date):
            raise Conflict(f"looks like a duplicate of {other.id}", param="expense")
    expense.status = "submitted"
    svc.store.bump(expense, now)
    view = expense_view(expense)
    svc.bus.emit("expense.submitted", {"expense": view})
    return view


@operation("expense.approve")
def approve(svc, params):
    now, expense, by = _decide(svc, params)
    if expense.status != "submitted":
        raise Conflict(f"expense {expense.id} is {expense.status}", param="expense")
    if by.id != _next_approver(svc, expense):
        raise Conflict(f"{by.name} is not the next approver", param="by")
    expense.approvals.append(by.id)
    if len(expense.approvals) == (2 if _needs_two(svc, expense) else 1):
        expense.status = "approved"
    svc.store.bump(expense, now)
    view = expense_view(expense)
    svc.bus.emit("expense.approved", {"expense": view})
    return view


@operation("expense.reject")
def reject(svc, params):
    reason = validate.require_str(params, "reason")
    now, expense, by = _decide(svc, params)
    if expense.status != "submitted":
        raise Conflict(f"expense {expense.id} is {expense.status}", param="expense")
    if by.id != _next_approver(svc, expense):
        raise Conflict(f"{by.name} is not the next approver", param="by")
    expense.status = "rejected"
    expense.reason = reason
    svc.store.bump(expense, now)
    view = expense_view(expense)
    svc.bus.emit("expense.rejected", {"expense": view})
    return view

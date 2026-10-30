"""Prices and team budgets."""
from .errors import InsufficientBudget
from .fmt import money


def price(room, start, end):
    """Cost in cents: the hourly rate for the minutes booked, rounded half up to a cent."""
    minutes = int((end - start).total_seconds() // 60)
    return (room.rate_cents * minutes * 2 + 60) // 120


def check_budget(team, cents):
    if cents > team.budget_cents:
        raise InsufficientBudget(
            f"team budget too low: need {money(cents)}, have {money(team.budget_cents)}")


def charge(team, cents):
    check_budget(team, cents)
    team.budget_cents -= cents
    team.spent_cents += cents


def refund(team, cents):
    team.budget_cents += cents
    team.spent_cents -= cents

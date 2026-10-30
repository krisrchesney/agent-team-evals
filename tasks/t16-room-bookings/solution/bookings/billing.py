"""Prices, fees and team budgets."""
from datetime import timedelta

from .errors import InsufficientBudget
from .fmt import money

SERIES_DISCOUNT_FROM = 4  # occurrences
FREE_CANCEL = timedelta(hours=24)
HALF_FEE_CANCEL = timedelta(hours=2)


def price(room, start, end):
    """Cost in cents: the hourly rate for the minutes booked, rounded half up to a cent."""
    minutes = int((end - start).total_seconds() // 60)
    return (room.rate_cents * minutes * 2 + 60) // 120


def series_price(cost, count):
    """One occurrence's cost in a series of `count`: 10% off from 4 occurrences, rounded half up."""
    if count < SERIES_DISCOUNT_FROM:
        return cost
    return (cost * 180 + 100) // 200


def cancellation_fee(cost, start, now):
    """What the team keeps: nothing with at least 24 hours to go, half (rounded half up) with at
    least 2 hours to go, everything closer than that."""
    ahead = start - now
    if ahead >= FREE_CANCEL:
        return 0
    if ahead >= HALF_FEE_CANCEL:
        return (cost + 1) // 2
    return cost


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


def settle_cancellation(team, cost, fee):
    """Give back `cost - fee` and record the fee."""
    refund(team, cost - fee)
    team.fees_cents += fee

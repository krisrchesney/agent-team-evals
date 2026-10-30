"""Business rules for a parsed transaction. The first rule that fails is the reason given."""
from decimal import Decimal

from .fx import is_known
from .models import Issue

STATUSES = ("paid", "void", "refunded")
MAX_ID = 20
MAX_LABEL = 40


def check(txn):
    """Return a message describing why `txn` is unusable, or None if it is fine."""
    if len(txn.id) > MAX_ID:
        return f"id longer than {MAX_ID} characters"
    if len(txn.region) > MAX_LABEL or len(txn.product) > MAX_LABEL:
        return f"region or product longer than {MAX_LABEL} characters"
    if txn.qty <= 0:
        return "qty must be positive"
    if txn.unit_price < 0:
        return "price must not be negative"
    if not Decimal(0) <= txn.discount_pct <= Decimal(100):
        return "discount must be between 0 and 100"
    if not is_known(txn.currency):
        return f"unknown currency '{txn.currency}'"
    if txn.currency == "JPY" and txn.unit_price != txn.unit_price.to_integral_value():
        return "price must be a whole number for JPY"
    if txn.status not in STATUSES:
        return f"unknown status '{txn.status}'"
    return None


def split_valid(txns):
    """Return (good, issues). A row that passes every rule uses up its id; a later row with the
    same id is rejected as a duplicate. Rows rejected for any other reason do not use up their id."""
    good, issues, seen = [], [], set()
    for txn in txns:
        problem = check(txn)
        if problem is None and txn.id in seen:
            problem = f"duplicate id '{txn.id}'"
        if problem:
            issues.append(Issue(txn.line, problem))
        else:
            seen.add(txn.id)
            good.append(txn)
    return good, issues

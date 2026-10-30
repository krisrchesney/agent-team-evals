"""Business rules for a parsed transaction. The first rule that fails is the reason given."""
from decimal import Decimal

from .fx import is_known

STATUSES = ("paid", "void")
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
    if txn.status not in STATUSES:
        return f"unknown status '{txn.status}'"
    return None

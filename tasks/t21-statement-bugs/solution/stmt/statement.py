"""Build a monthly statement (docs/STATEMENTS.md)."""
from dataclasses import dataclass, field

from .balances import balance_before, counted
from .periods import month_period


@dataclass
class Statement:
    account: object
    year: int
    month: int
    opening_cents: int
    lines: list = field(default_factory=list)   # Txn objects, in statement order
    closing_cents: int = 0


def build_statement(store, account, year, month):
    start, end = month_period(year, month, account.utc_offset_minutes)
    opening = balance_before(store, account.id, start)
    lines = [t for t in counted(store, account.id) if start <= t.posted_at < end]
    lines.sort(key=lambda t: (t.posted_at, t.external_id))
    closing = opening + sum(t.amount_cents for t in lines)
    return Statement(account, year, month, opening, lines, closing)

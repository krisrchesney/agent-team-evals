"""Plain data passed between the pipeline stages."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Txn:
    """One accepted-by-the-parser input row. `line` is its 1-based line in the file."""

    id: str
    date: date
    region: str
    product: str
    qty: int
    unit_price: Decimal
    discount_pct: Decimal
    currency: str
    status: str
    line: int


@dataclass(frozen=True)
class Issue:
    """A row that was skipped, and why."""

    line: int
    message: str


@dataclass(frozen=True)
class Line:
    """A transaction priced in USD."""

    txn: Txn
    usd: Decimal


@dataclass
class Group:
    """One row of the report."""

    label: str
    orders: int = 0
    units: int = 0
    revenue: Decimal = Decimal("0.00")

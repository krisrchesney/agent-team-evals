"""Money helpers. Every amount in the ledger is an integer number of cents.

Text goes in and out only through the functions here, so the rules live in one place.
Rounding is half away from zero, everywhere.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .errors import InvalidAmount


def parse_amount(text):
    """'12.50' -> 1250. At most two decimals. A plain int is a whole number of dollars."""
    if isinstance(text, bool):
        raise InvalidAmount("amount must be text or a whole number", param="amount")
    if isinstance(text, int):
        return text * 100
    try:
        value = Decimal(str(text).strip().replace(",", ""))
    except InvalidOperation:
        raise InvalidAmount(f"not an amount: {text!r}", param="amount") from None
    if not value.is_finite() or value != value.quantize(Decimal("0.01")):
        raise InvalidAmount(f"amount {text!r} must have at most 2 decimals", param="amount")
    return int(value * 100)


def format_amount(cents):
    """1234550 -> '$12,345.50'."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{frac:02d}"


def to_decimal_string(cents):
    """1250 -> '12.50' (no symbol, no separators)."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"


def percent(cents, basis_points):
    """cents * basis_points / 10000, rounded half away from zero."""
    exact = Decimal(cents) * Decimal(basis_points) / Decimal(10000)
    rounded = exact.copy_abs().quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(rounded) if exact >= 0 else -int(rounded)


def split_evenly(cents, parts):
    """Split into `parts` shares that add up exactly; the first shares get the extra cents."""
    base, extra = divmod(abs(cents), parts)
    sign = -1 if cents < 0 else 1
    return [sign * (base + (1 if i < extra else 0)) for i in range(parts)]

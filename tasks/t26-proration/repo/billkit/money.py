"""Money is whole cents everywhere; these helpers turn other numbers into cents."""
from decimal import ROUND_HALF_UP, Decimal


def round_cents(value):
    """Round a Decimal/int/float amount of cents to a whole number, halves away from zero."""
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def format_cents(cents, currency="USD"):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{frac:02d} {currency}"


def percent_of(cents, percent):
    """`percent` is a whole or fractional percentage, e.g. 12.5."""
    return round_cents(Decimal(cents) * Decimal(str(percent)) / Decimal(100))


def basis_points_of(cents, bps):
    return round_cents(Decimal(cents) * Decimal(bps) / Decimal(10000))


def split_evenly(cents, parts):
    """Split cents into `parts` shares that add up exactly; the first shares get the extra cents."""
    if parts < 1:
        raise ValueError("parts must be at least 1")
    base, extra = divmod(cents, parts)
    return [base + (1 if i < extra else 0) for i in range(parts)]

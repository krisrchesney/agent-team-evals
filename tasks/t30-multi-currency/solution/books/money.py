"""Money helpers. Every amount in the ledger is an integer in the minor unit of its currency.

Text goes in and out only through the functions here, so the rules live in one place.
Rounding is half away from zero, everywhere.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .errors import InvalidAmount, UnknownCurrency

EXPONENTS = {"USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3}


def exponent(currency):
    try:
        return EXPONENTS[currency]
    except (KeyError, TypeError):
        raise UnknownCurrency(f"unknown currency {currency!r}", param="currency") from None


def parse_amount(text, currency="USD"):
    """'12.50' -> 1250 for USD. At most as many decimals as the currency has. A plain int is whole units."""
    digits = exponent(currency)
    if isinstance(text, bool):
        raise InvalidAmount("amount must be text or a whole number", param="amount")
    if isinstance(text, int):
        return text * 10 ** digits
    try:
        value = Decimal(str(text).strip().replace(",", ""))
    except InvalidOperation:
        raise InvalidAmount(f"not an amount: {text!r}", param="amount") from None
    if not value.is_finite() or value != value.quantize(Decimal(1).scaleb(-digits)):
        raise InvalidAmount(f"amount {text!r} must have at most {digits} decimals", param="amount")
    return int(value.scaleb(digits))


def _plain(minor, currency):
    digits = exponent(currency)
    whole, frac = divmod(abs(minor), 10 ** digits)
    return whole, (f"{frac:0{digits}d}" if digits else "")


def format_amount(minor, currency="USD"):
    """USD: 1234550 -> '$12,345.50'. Other currencies: 1234550 EUR -> '12,345.50 EUR'."""
    whole, frac = _plain(minor, currency)
    body = f"{whole:,}" + (f".{frac}" if frac else "")
    sign = "-" if minor < 0 else ""
    return f"{sign}${body}" if currency == "USD" else f"{sign}{body} {currency}"


def to_decimal_string(minor, currency="USD"):
    """1250 -> '12.50' (no symbol, no separators)."""
    whole, frac = _plain(minor, currency)
    sign = "-" if minor < 0 else ""
    return f"{sign}{whole}" + (f".{frac}" if frac else "")


def round_half_away(exact):
    rounded = exact.copy_abs().quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(rounded) if exact >= 0 else -int(rounded)


def percent(minor, basis_points):
    """minor * basis_points / 10000, rounded half away from zero."""
    return round_half_away(Decimal(minor) * Decimal(basis_points) / Decimal(10000))


def split_evenly(minor, parts):
    """Split into `parts` shares that add up exactly; the first shares get the extra units."""
    base, extra = divmod(abs(minor), parts)
    sign = -1 if minor < 0 else 1
    return [sign * (base + (1 if i < extra else 0)) for i in range(parts)]

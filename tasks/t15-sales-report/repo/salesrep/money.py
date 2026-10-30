"""Decimal helpers. All amounts are Decimal; nothing here touches floats."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def to_decimal(text):
    """Parse a plain decimal number such as '12', '-3.50' or '.5'. Raises ValueError otherwise."""
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(text) from None
    if not value.is_finite():
        raise ValueError(text)
    return value


def quantize(value, places=2):
    """Round half away from zero to `places` decimal places."""
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def format_money(value):
    """12345.5 -> '12,345.50'."""
    return f"{quantize(value):,.2f}"

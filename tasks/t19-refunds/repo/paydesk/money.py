"""Amounts are ints in the currency's minor unit (cents for USD, yen for JPY)."""
from .currencies import CURRENCIES
from .errors import InvalidRequest


def check_amount(value, param="amount"):
    """A positive int. bool is rejected even though it is an int subclass. Returns the value."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{param} must be an integer", code="invalid_amount", param=param)
    if value <= 0:
        raise InvalidRequest(f"{param} must be positive", code="invalid_amount", param=param)
    return value


def check_currency(value, param="currency"):
    if value not in CURRENCIES:
        raise InvalidRequest(f"unsupported currency: {value!r}", code="invalid_currency", param=param)
    return value


def format_amount(amount, currency):
    """2500, "USD" -> "25.00 USD"; 500, "JPY" -> "500 JPY"."""
    places = CURRENCIES[currency]
    sign = "-" if amount < 0 else ""
    whole, frac = divmod(abs(amount), 10 ** places)
    if places == 0:
        return f"{sign}{whole} {currency}"
    return f"{sign}{whole}.{frac:0{places}d} {currency}"

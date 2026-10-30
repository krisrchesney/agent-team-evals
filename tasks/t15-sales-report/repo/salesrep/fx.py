"""Exchange rates into USD."""
from decimal import Decimal

from .money import quantize

RATES = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.08"),
    "GBP": Decimal("1.27"),
}


def is_known(currency):
    return currency in RATES


def to_usd(amount, currency):
    """Convert `amount` to USD, rounded half up to cents."""
    return quantize(amount * RATES[currency], 2)

"""Shipping charge."""

SHIPPING_CENTS = 700
FREE_SHIPPING_MIN_CENTS = 5000


def shipping_cost(amount):
    """Shipping for a non-empty cart whose goods are worth `amount` cents."""
    if amount >= FREE_SHIPPING_MIN_CENTS:
        return 0
    return SHIPPING_CENTS

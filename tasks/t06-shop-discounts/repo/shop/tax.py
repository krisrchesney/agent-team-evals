"""Sales tax. Rates are in basis points (825 = 8.25%)."""

RATES_BP = {"general": 825, "food": 0, "books": 500}


def round_half_up_div(numerator, denominator):
    """numerator / denominator rounded to the nearest integer, halves up (non-negative inputs)."""
    return (2 * numerator + denominator) // (2 * denominator)


def line_tax(category, taxable, amount_cents):
    if not taxable:
        return 0
    rate = RATES_BP.get(category, RATES_BP["general"])
    return round_half_up_div(amount_cents * rate, 10000)

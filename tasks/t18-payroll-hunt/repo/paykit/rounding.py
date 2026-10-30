"""Integer rounding helpers. Money never goes through floating point."""


def half_up_div(numerator, denominator):
    """numerator / denominator rounded to a whole number, halves rounding up.

    Both arguments are non-negative ints and the denominator is positive.
    """
    return (2 * numerator + denominator) // (2 * denominator)


def round_quarter_hour(minutes):
    """Round a number of minutes to the nearest multiple of 15."""
    return (minutes + 7) // 15 * 15

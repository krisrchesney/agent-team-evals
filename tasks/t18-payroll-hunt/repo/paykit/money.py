"""Text forms of money and hours."""


def format_cents(cents):
    """Dollars and cents with a dollar sign and thousands separators: 123456 -> '$1,234.56'."""
    sign = "-" if cents < 0 else ""
    dollars, rest = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rest:02d}"


def format_hours(minutes):
    """Minutes as hours with exactly two decimals: 450 -> '7.50', 0 -> '0.00'."""
    return str(round(minutes / 60, 2))

"""Money helpers. Amounts are integer cents."""
import re

CURRENCIES = {"USD", "EUR", "GBP", "CHF", "SEK"}


def to_cents(text, decimal_sep=".", thousands_sep=","):
    """Parse a non-negative price in the given number format into cents.

    "1,234.50" -> 123450 with the defaults; "1.234,50" -> 123450 with decimal_sep=",",
    thousands_sep=".". Thousands separators must group digits in threes. At most two decimals.
    Raises ValueError for anything else, including a sign.
    """
    text = text.strip()
    d, t = re.escape(decimal_sep), re.escape(thousands_sep)
    pattern = rf"(\d{{1,3}}(?:{t}\d{{3}})+|\d+)(?:{d}(\d{{1,2}}))?"
    match = re.fullmatch(pattern, text)
    if not match:
        raise ValueError(f"not an amount: {text!r}")
    whole = int(match.group(1).replace(thousands_sep, ""))
    frac = (match.group(2) or "").ljust(2, "0")
    return whole * 100 + int(frac)


def format_cents(cents, currency):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{frac:02d} {currency}"

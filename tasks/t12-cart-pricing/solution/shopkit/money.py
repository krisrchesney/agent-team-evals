"""Money helpers. Amounts are whole cents (int); rates are basis points (1 bp = 0.01%)."""

BP_SCALE = 10_000


def pct(amount, bp):
    """`bp` basis points of `amount`, as whole cents, rounded half up."""
    return (amount * bp + BP_SCALE // 2) // BP_SCALE


def format_cents(cents):
    sign = "-" if cents < 0 else ""
    dollars, rest = divmod(abs(cents), 100)
    return f"{sign}${dollars}.{rest:02d}"

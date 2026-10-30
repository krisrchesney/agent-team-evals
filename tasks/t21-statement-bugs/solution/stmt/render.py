"""Plain-text rendering of a statement."""
from .periods import local_date


def money(cents):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{frac:02d}"


def render(statement):
    account = statement.account
    out = [f"Statement for {account.name} ({account.id}), {statement.year}-{statement.month:02d}",
           f"Opening balance: {money(statement.opening_cents)}"]
    for txn in statement.lines:
        day = local_date(txn.posted_at, account.utc_offset_minutes).isoformat()
        out.append(f"{day}  {txn.description:<32} {money(txn.amount_cents):>12}")
    if not statement.lines:
        out.append("(no transactions)")
    out.append(f"Closing balance: {money(statement.closing_cents)}")
    return "\n".join(out) + "\n"

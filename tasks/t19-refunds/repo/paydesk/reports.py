"""Read-only summaries for the back office."""
from .money import format_amount


def revenue_by_currency(ledger):
    """{"USD": 12345, ...}: merchant revenue per currency, from the ledger."""
    totals = {}
    for txn in ledger.transactions:
        for account, amount in txn["entries"]:
            if account == "merchant_revenue":
                totals[txn["currency"]] = totals.get(txn["currency"], 0) + amount
    return dict(sorted(totals.items()))


def revenue_report(ledger):
    lines = ["Revenue"]
    for currency, amount in revenue_by_currency(ledger).items():
        lines.append(f"  {format_amount(amount, currency)}")
    if len(lines) == 1:
        lines.append("  (none)")
    return "\n".join(lines) + "\n"


def charges_by_status(store):
    counts = {}
    for charge in store.charges.values():
        counts[charge.status] = counts.get(charge.status, 0) + 1
    return dict(sorted(counts.items()))

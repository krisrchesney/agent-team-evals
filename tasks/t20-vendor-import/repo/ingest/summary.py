"""Totals for the finance dashboard."""
from .money import format_cents


def totals_by_currency(records):
    totals = {}
    for record in records:
        totals[record.currency] = totals.get(record.currency, 0) + record.total_cents
    return dict(sorted(totals.items()))


def summary_text(result):
    lines = [f"{result.vendor}: {len(result.records)} lines, {len(result.errors)} rejected"]
    for currency, cents in totals_by_currency(result.records).items():
        lines.append(f"  {format_cents(cents, currency)}")
    for error in result.errors:
        lines.append(f"  line {error.line}: {error.code}")
    return "\n".join(lines) + "\n"

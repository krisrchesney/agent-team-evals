"""Turn an Order into a Quote."""
from dataclasses import dataclass

from .tax import line_tax


@dataclass(frozen=True)
class LineQuote:
    sku: str
    name: str
    qty: int
    unit_cents: int
    gross_cents: int
    tax_cents: int


@dataclass(frozen=True)
class Quote:
    lines: tuple
    subtotal_cents: int
    tax_cents: int
    total_cents: int


def price_order(order, catalog):
    lines = []
    for line in order.lines:
        item = catalog.get(line.sku)
        gross = item.price_cents * line.qty
        tax = line_tax(item.category, item.taxable, gross)
        lines.append(LineQuote(item.sku, item.name, line.qty, item.price_cents, gross, tax))
    subtotal = sum(l.gross_cents for l in lines)
    tax = sum(l.tax_cents for l in lines)
    return Quote(tuple(lines), subtotal, tax, subtotal + tax)

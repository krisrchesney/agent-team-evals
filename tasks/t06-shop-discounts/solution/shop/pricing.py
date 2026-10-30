"""Turn an Order into a Quote."""
from dataclasses import dataclass

from .coupons import apply_coupons
from .tax import line_tax


@dataclass(frozen=True)
class LineQuote:
    sku: str
    name: str
    qty: int
    unit_cents: int
    gross_cents: int
    tax_cents: int
    bundle_discount_cents: int = 0
    coupon_discount_cents: int = 0

    @property
    def discount_cents(self):
        return self.bundle_discount_cents + self.coupon_discount_cents

    @property
    def net_cents(self):
        return self.gross_cents - self.discount_cents


@dataclass(frozen=True)
class Quote:
    lines: tuple
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    discount_cents: int = 0
    coupons: tuple = ()


def bundle_discount(item, qty):
    if item.bundle is None:
        return 0
    n, m = item.bundle
    return (qty - (qty // n * m + qty % n)) * item.price_cents


def price_order(order, catalog):
    items = [catalog.get(line.sku) for line in order.lines]
    gross = [it.price_cents * line.qty for it, line in zip(items, order.lines)]
    bundle = [bundle_discount(it, line.qty) for it, line in zip(items, order.lines)]
    coupon, applied = apply_coupons(
        order.coupons, [g - b for g, b in zip(gross, bundle)], [it.category for it in items])
    lines = []
    for it, line, g, b, c in zip(items, order.lines, gross, bundle, coupon):
        tax = line_tax(it.category, it.taxable, g - b - c)
        lines.append(LineQuote(it.sku, it.name, line.qty, it.price_cents, g, tax, b, c))
    subtotal = sum(gross)
    discount = sum(l.discount_cents for l in lines)
    tax = sum(l.tax_cents for l in lines)
    return Quote(tuple(lines), subtotal, tax, subtotal - discount + tax, discount, tuple(applied))

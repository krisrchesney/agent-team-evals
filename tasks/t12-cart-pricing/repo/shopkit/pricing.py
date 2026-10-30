"""Turn cart lines and coupons into a price breakdown."""
from .money import pct
from .shipping import shipping_cost

BULK_QTY = 10
BULK_BP = 1000


def line_price(unit_price, qty):
    return unit_price * qty


def bulk_discount(unit_price, qty):
    """Discount for one line; large quantities get a percentage off."""
    if qty > BULK_QTY:
        return pct(line_price(unit_price, qty), BULK_BP)
    return 0


def apply_coupons(amount, coupons):
    """The amount left after all coupons."""
    # Fixed-amount coupons go first so that percent coupons act on the already reduced amount.
    for coupon in sorted(coupons, key=lambda c: c.kind != "fixed"):
        amount = coupon.apply(amount)
    return amount


def price(lines, coupons, tax_bp):
    """`lines` is a list of [sku, unit_price, qty]. Returns the breakdown dict."""
    subtotal = sum(line_price(p, q) for _, p, q in lines)
    bulk = sum(bulk_discount(p, q) for _, p, q in lines)
    after_bulk = subtotal - bulk
    after_coupons = apply_coupons(after_bulk, coupons)
    tax = pct(after_coupons, tax_bp)
    shipping = shipping_cost(after_bulk) if lines else 0
    return {
        "subtotal": subtotal,
        "bulk_discount": bulk,
        "coupon_discount": after_bulk - after_coupons,
        "tax": tax,
        "shipping": shipping,
        "total": after_coupons + tax + shipping,
    }

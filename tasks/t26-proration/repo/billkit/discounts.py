"""Applying coupons to invoice lines."""
from .errors import Conflict, ValidationError
from .invoices import Line
from .money import percent_of


def find_coupon(app, code):
    code = code.strip()
    for coupon in app.coupons.all():
        if coupon.code.lower() == code.lower():
            return coupon
    raise ValidationError(f"unknown coupon {code!r}", field="coupon")


def redeem(app, code, redemptions):
    """`redemptions` is a dict of code -> times used so far; the caller owns that state."""
    coupon = find_coupon(app, code)
    used = redemptions.get(coupon.code, 0)
    if coupon.max_redemptions and used >= coupon.max_redemptions:
        raise Conflict("coupon has been used up", field="coupon")
    redemptions[coupon.code] = used + 1
    return coupon


def discount_line(coupon, invoice):
    """A negative line worth `coupon.percent` of the invoice's positive lines."""
    base = sum(line.amount_cents for line in invoice.lines if line.amount_cents > 0)
    cents = percent_of(base, coupon.percent)
    first = invoice.lines[0]
    return Line(f"Coupon {coupon.code} ({coupon.percent}%)", -cents, first.period_start, first.period_end,
                "discount")

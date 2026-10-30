"""Plain-text invoice."""


def money(cents):
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def render_invoice(quote):
    out = []
    for l in quote.lines:
        out.append(f"{l.name:<16}{l.qty:>3} x {money(l.unit_cents):>7} {money(l.gross_cents):>9}")
    out.append(f"Subtotal: {money(quote.subtotal_cents)}")
    if quote.discount_cents:
        for l in quote.lines:
            if l.bundle_discount_cents:
                out.append(f"  Bundle {l.name}: -{money(l.bundle_discount_cents)}")
        for c in quote.coupons:
            out.append(f"  Coupon {c.code}: -{money(c.amount_cents)}")
        out.append(f"Discount: -{money(quote.discount_cents)}")
    out.append(f"Tax: {money(quote.tax_cents)}")
    out.append(f"Total: {money(quote.total_cents)}")
    return "\n".join(out)

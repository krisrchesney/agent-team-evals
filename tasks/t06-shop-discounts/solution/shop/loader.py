"""Build catalogs and orders from plain dicts (parsed JSON) and turn quotes back into dicts."""
from .catalog import Catalog
from .models import Item, Line, Order


def catalog_from_list(rows):
    return Catalog(
        Item(
            sku=r["sku"],
            name=r["name"],
            price_cents=r["price_cents"],
            category=r.get("category", "general"),
            taxable=r.get("taxable", True),
            bundle=tuple(r["bundle"]) if r.get("bundle") is not None else None,
        )
        for r in rows
    )


def order_from_dict(data):
    lines = tuple(Line(r["sku"], r["qty"]) for r in data["lines"])
    return Order(lines, customer=data.get("customer", ""), coupons=tuple(data.get("coupons", ())))


def quote_to_dict(quote):
    return {
        "lines": [
            {
                "sku": l.sku,
                "name": l.name,
                "qty": l.qty,
                "unit_cents": l.unit_cents,
                "gross_cents": l.gross_cents,
                "tax_cents": l.tax_cents,
                "bundle_discount_cents": l.bundle_discount_cents,
                "coupon_discount_cents": l.coupon_discount_cents,
                "net_cents": l.net_cents,
            }
            for l in quote.lines
        ],
        "subtotal_cents": quote.subtotal_cents,
        "discount_cents": quote.discount_cents,
        "coupons": [{"code": c.code, "amount_cents": c.amount_cents} for c in quote.coupons],
        "tax_cents": quote.tax_cents,
        "total_cents": quote.total_cents,
    }

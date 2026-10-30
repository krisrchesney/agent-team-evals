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
        )
        for r in rows
    )


def order_from_dict(data):
    lines = tuple(Line(r["sku"], r["qty"]) for r in data["lines"])
    return Order(lines, customer=data.get("customer", ""))


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
            }
            for l in quote.lines
        ],
        "subtotal_cents": quote.subtotal_cents,
        "tax_cents": quote.tax_cents,
        "total_cents": quote.total_cents,
    }

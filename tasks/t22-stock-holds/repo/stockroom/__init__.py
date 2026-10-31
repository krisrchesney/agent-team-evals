"""stockroom: stock levels for a small online shop.

    from stockroom import Service
    svc = Service()
    item = svc.call("item.create", sku="MUG-01", name="Mug")
    svc.call("stock.receive", item=item["id"], quantity=12)
"""
from .service import Service

__all__ = ["Service"]

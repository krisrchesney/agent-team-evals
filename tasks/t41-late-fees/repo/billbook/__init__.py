"""billbook: invoices and the payments made against them. Amounts are whole cents, dates are YYYY-MM-DD.

    from billbook import Service
    svc = Service()
    inv = svc.call("invoice.create", customer="cus-1", amount=50000, due="2026-02-01")
    svc.call("invoice.pay", invoice=inv["id"], amount=20000)
"""
from .service import Service

__all__ = ["Service"]

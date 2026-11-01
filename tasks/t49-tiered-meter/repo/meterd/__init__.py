"""meterd: usage metering and invoices for a small SaaS.

    from meterd import Service
    svc = Service()
    cust = svc.call("customer.create", name="Acme")
    svc.call("usage.record", customer=cust["id"], meter="units", quantity=40)
    invoice = svc.call("period.close", customer=cust["id"])
"""
from .service import Service

__all__ = ["Service"]

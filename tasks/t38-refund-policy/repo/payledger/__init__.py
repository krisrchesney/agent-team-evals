"""payledger: card charges and their ledger entries for a small shop. Amounts are whole cents.

    from payledger import Service
    svc = Service()
    charge = svc.call("charge.create", customer="cus-1", amount=2500, tax=200)
"""
from .service import Service

__all__ = ["Service"]

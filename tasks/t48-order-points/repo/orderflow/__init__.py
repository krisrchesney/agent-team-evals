"""orderflow: orders that move from placed to delivered.

    from orderflow import Service
    svc = Service()
    order = svc.call("order.place", customer="ada", total=2500)
    svc.call("order.pay", order=order["id"])
"""
from .service import Service

__all__ = ["Service"]

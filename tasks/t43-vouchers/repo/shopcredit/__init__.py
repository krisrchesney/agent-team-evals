"""shopcredit: customers and their orders for a small online shop. Money is whole cents (an int); times are UTC.

    from shopcredit import Service
    svc = Service()
    kim = svc.call("customer.create", name="Kim")
    order = svc.call("order.create", customer=kim["id"], total=4500)
    svc.call("order.pay", order=order["id"])
"""
from .service import Service

__all__ = ["Service"]

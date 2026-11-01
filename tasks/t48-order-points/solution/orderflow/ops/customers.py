from .. import validate
from .registry import operation


@operation("customer.points")
def points(svc, params):
    customer = validate.require_str(params, "customer")
    return {"customer": customer, "balance": svc.store.points.get(customer, 0)}

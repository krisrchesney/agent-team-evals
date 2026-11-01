from .. import validate
from ..models import Customer
from ..views import customer_view
from .registry import operation


@operation("customer.create")
def create(svc, params):
    now = svc.clock.now()
    name = validate.require_str(params, "name")
    customer = Customer(id=svc.ids.new("customer"), name=name, created_at=now, updated_at=now)
    svc.store.customers[customer.id] = customer
    view = customer_view(customer)
    svc.bus.emit("customer.created", {"customer": view})
    return view


@operation("customer.retrieve")
def retrieve(svc, params):
    return customer_view(svc.store.get_customer(validate.require_str(params, "customer")))

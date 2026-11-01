from .. import validate
from ..errors import Conflict
from ..models import Order
from ..views import order_view
from .registry import operation


@operation("order.create")
def create(svc, params):
    now = svc.clock.now()
    customer = svc.store.get_customer(validate.require_str(params, "customer"))
    total = validate.cents(params, "total")
    order = Order(id=svc.ids.new("order"), customer=customer.id, total=total, status="open",
                  created_at=now, updated_at=now)
    svc.store.orders[order.id] = order
    view = order_view(order)
    svc.bus.emit("order.created", {"order": view})
    return view


@operation("order.pay")
def pay(svc, params):
    now = svc.clock.now()
    order = svc.store.get_order(validate.require_str(params, "order"))
    if order.status != "open":
        raise Conflict(f"order {order.id} is already {order.status}", param="order")
    order.status = "paid"
    svc.store.bump(order, now)
    view = order_view(order)
    svc.bus.emit("order.paid", {"order": view})
    return view


@operation("order.retrieve")
def retrieve(svc, params):
    return order_view(svc.store.get_order(validate.require_str(params, "order")))

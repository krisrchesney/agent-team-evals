from .. import validate
from ..errors import Conflict
from ..models import Order
from ..views import order_view
from .registry import operation

# action: (statuses it can start from, status it leads to)
MOVES = {
    "pay": (("placed",), "paid"),
    "pack": (("paid",), "packed"),
    "ship": (("packed",), "shipped"),
    "deliver": (("shipped",), "delivered"),
    "cancel": (("placed", "paid", "packed"), "cancelled"),
}


@operation("order.place")
def place(svc, params):
    now = svc.clock.now()
    customer = validate.require_str(params, "customer")
    total = validate.require_total(params)
    order = Order(id=svc.ids.new("order"), customer=customer, total=total, status="placed",
                  created_at=now, updated_at=now)
    svc.store.orders[order.id] = order
    view = order_view(order)
    svc.bus.emit("order.placed", {"order": view})
    return view


def move(action):
    """The operation `order.<action>`: check, change status, then let the reactions have their say."""
    sources, target = MOVES[action]

    def run(svc, params):
        now = svc.clock.now()
        order = svc.store.get_order(validate.require_str(params, "order"))
        if order.status not in sources:
            raise Conflict(f"order {order.id} is {order.status}, it cannot be moved by {action}", param="order")
        for reaction in svc.reactions:
            reaction.check(svc, order, action)
        order.status = target
        svc.store.bump(order, now)
        view = order_view(order)
        events = [(f"order.{target}", {"order": view})]
        for reaction in svc.reactions:
            events.extend(reaction.apply(svc, order, action))
        for type_, data in events:
            svc.bus.emit(type_, data)
        return view

    return run


for _action in MOVES:
    operation(f"order.{_action}")(move(_action))


@operation("order.retrieve")
def retrieve(svc, params):
    return order_view(svc.store.get_order(validate.require_str(params, "order")))


@operation("order.list")
def list_orders(svc, params):
    limit = validate.limit(params)
    orders = sorted(svc.store.orders.values(), key=lambda o: (o.created_at, o.id))
    return {"data": [order_view(o) for o in orders[:limit]], "has_more": len(orders) > limit}

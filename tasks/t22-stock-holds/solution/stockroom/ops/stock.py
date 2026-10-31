from .. import validate
from ..errors import InsufficientStock
from ..views import available, item_view, movement_view
from .registry import operation


@operation("stock.receive")
def receive(svc, params):
    now = svc.clock.now()
    svc.store.expire_holds(now)
    item = svc.store.get_item(validate.require_str(params, "item"))
    quantity = validate.require_qty(params)
    ref = validate.optional_str(params, "ref", "delivery")
    item.on_hand += quantity
    svc.store.bump(item, now)
    mv = svc.store.add_movement(svc.ids, item, "receive", quantity, ref, now)
    view = item_view(svc, item)
    svc.bus.emit("stock.received", {"item": view, "movement": movement_view(mv)})
    return view


@operation("stock.ship")
def ship(svc, params):
    now = svc.clock.now()
    svc.store.expire_holds(now)
    item = svc.store.get_item(validate.require_str(params, "item"))
    quantity = validate.require_qty(params)
    order = validate.require_str(params, "order")
    if quantity > available(svc, item):
        raise InsufficientStock(f"only {available(svc, item)} of {item.sku} available", param="quantity")
    item.on_hand -= quantity
    svc.store.bump(item, now)
    mv = svc.store.add_movement(svc.ids, item, "ship", -quantity, order, now)
    view = item_view(svc, item)
    svc.bus.emit("stock.shipped", {"item": view, "movement": movement_view(mv)})
    return view


@operation("stock.adjust")
def adjust(svc, params):
    now = svc.clock.now()
    svc.store.expire_holds(now)
    item = svc.store.get_item(validate.require_str(params, "item"))
    delta = validate.require_delta(params)
    reason = validate.require_str(params, "reason")
    if item.on_hand + delta < 0:
        raise InsufficientStock(f"{item.sku} has only {item.on_hand} on hand", param="delta")
    item.on_hand += delta
    svc.store.bump(item, now)
    mv = svc.store.add_movement(svc.ids, item, "adjust", delta, reason, now)
    view = item_view(svc, item)
    svc.bus.emit("stock.adjusted", {"item": view, "movement": movement_view(mv)})
    return view


@operation("stock.movements")
def movements(svc, params):
    item = svc.store.get_item(validate.require_str(params, "item"))
    limit = validate.limit(params)
    mvs = svc.store.movements_for(item.id)
    return {"data": [movement_view(m) for m in mvs[:limit]], "has_more": len(mvs) > limit}

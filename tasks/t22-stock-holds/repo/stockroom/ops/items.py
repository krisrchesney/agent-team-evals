from .. import validate
from ..errors import Conflict
from ..models import Item
from ..views import item_view
from .registry import operation


@operation("item.create")
def create(svc, params):
    now = svc.clock.now()
    sku = validate.require_str(params, "sku").upper()
    name = validate.require_str(params, "name")
    if any(i.sku == sku for i in svc.store.items.values()):
        raise Conflict(f"sku {sku} already exists", param="sku")
    item = Item(id=svc.ids.new("item"), sku=sku, name=name, on_hand=0, created_at=now, updated_at=now)
    svc.store.items[item.id] = item
    view = item_view(svc, item)
    svc.bus.emit("item.created", {"item": view})
    return view


@operation("item.retrieve")
def retrieve(svc, params):
    item = svc.store.get_item(validate.require_str(params, "item"))
    return item_view(svc, item)


@operation("item.list")
def list_items(svc, params):
    limit = validate.limit(params)
    items = sorted(svc.store.items.values(), key=lambda i: (i.created_at, i.id))
    return {"data": [item_view(svc, i) for i in items[:limit]], "has_more": len(items) > limit}

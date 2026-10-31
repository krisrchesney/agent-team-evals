def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def available(svc, item):
    return item.on_hand - svc.store.held(item.id)


def item_view(svc, item):
    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "on_hand": item.on_hand,
        "available": available(svc, item),
        "created_at": stamp(item.created_at),
        "updated_at": stamp(item.updated_at),
        "version": item.version,
    }


def movement_view(mv):
    return {"id": mv.id, "item": mv.item, "kind": mv.kind, "delta": mv.delta, "ref": mv.ref,
            "at": stamp(mv.at)}


def hold_view(hold):
    return {"id": hold.id, "item": hold.item, "order": hold.order, "quantity": hold.quantity,
            "status": hold.status, "expires_at": stamp(hold.expires_at),
            "created_at": stamp(hold.created_at), "updated_at": stamp(hold.updated_at),
            "version": hold.version}

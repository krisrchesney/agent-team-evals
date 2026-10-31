def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def available(svc, item):
    return item.on_hand


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

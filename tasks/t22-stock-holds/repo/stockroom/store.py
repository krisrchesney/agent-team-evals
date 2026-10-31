from .errors import NotFound
from .models import Movement


class Store:
    def __init__(self):
        self.items = {}
        self.movements = []

    def get_item(self, item_id):
        item = self.items.get(item_id)
        if item is None:
            raise NotFound(f"no item {item_id!r}", param="item")
        return item

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def add_movement(self, ids, item, kind, delta, ref, now):
        mv = Movement(id=ids.new("mv"), item=item.id, kind=kind, delta=delta, ref=ref, at=now)
        self.movements.append(mv)
        return mv

    def movements_for(self, item_id):
        return [m for m in self.movements if m.item == item_id]

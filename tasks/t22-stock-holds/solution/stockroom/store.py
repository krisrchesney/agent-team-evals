from .errors import NotFound
from .models import Movement


class Store:
    def __init__(self):
        self.items = {}
        self.movements = []
        self.holds = {}

    def get_item(self, item_id):
        item = self.items.get(item_id)
        if item is None:
            raise NotFound(f"no item {item_id!r}", param="item")
        return item

    def get_hold(self, hold_id):
        hold = self.holds.get(hold_id)
        if hold is None:
            raise NotFound(f"no hold {hold_id!r}", param="hold")
        return hold

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def add_movement(self, ids, item, kind, delta, ref, now):
        mv = Movement(id=ids.new("mv"), item=item.id, kind=kind, delta=delta, ref=ref, at=now)
        self.movements.append(mv)
        return mv

    def movements_for(self, item_id):
        return [m for m in self.movements if m.item == item_id]

    def expire_holds(self, now):
        """Holds expire lazily: every operation that reads or uses availability calls this first."""
        for hold in self.holds.values():
            if hold.status == "active" and now >= hold.expires_at:
                hold.status = "expired"
                self.bump(hold, now)

    def held(self, item_id):
        return sum(h.quantity for h in self.holds.values() if h.item == item_id and h.status == "active")

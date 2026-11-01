from .errors import NotFound


class Store:
    def __init__(self):
        self.orders = {}
        self.points = {}   # customer -> balance

    def get_order(self, order_id):
        order = self.orders.get(order_id)
        if order is None:
            raise NotFound(f"no order {order_id!r}", param="order")
        return order

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

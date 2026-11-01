from .base import Reaction
from .registry import reaction


@reaction
class Points(Reaction):
    """Loyalty points for delivered orders: 1 per full POINT_CENTS, at most DAILY_CAP per customer per day."""
    priority = 50
    POINT_CENTS = 1000
    DAILY_CAP = 50

    def fresh(self):
        return {"earned": {}}

    def apply(self, svc, order, action):
        if action != "deliver":
            return []
        earned = self.state["earned"]
        room = self.DAILY_CAP - earned.get(order.customer, 0)
        credit = min(order.total // self.POINT_CENTS, room)
        if credit <= 0:
            return []
        earned[order.customer] = earned.get(order.customer, 0) + credit
        balance = svc.store.points.get(order.customer, 0) + credit
        svc.store.points[order.customer] = balance
        return [("points.awarded", {"points": {"order": order.id, "customer": order.customer,
                                                "points": credit, "balance": balance}})]

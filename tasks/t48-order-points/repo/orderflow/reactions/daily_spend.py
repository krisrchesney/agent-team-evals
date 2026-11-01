from .base import Reaction
from .registry import reaction


@reaction
class DailySpend(Reaction):
    """A customer can pay for at most LIMIT cents of orders per day."""
    priority = 20
    LIMIT = 200_000

    def fresh(self):
        return {"spent": {}}

    def check(self, svc, order, action):
        if action == "pay" and self.state["spent"].get(order.customer, 0) + order.total > self.LIMIT:
            self.refuse(f"{order.customer} would pass the daily spend limit")

    def apply(self, svc, order, action):
        if action == "pay":
            spent = self.state["spent"]
            spent[order.customer] = spent.get(order.customer, 0) + order.total
        return []

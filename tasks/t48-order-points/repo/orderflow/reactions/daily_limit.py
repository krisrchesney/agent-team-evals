from .base import Reaction
from .registry import reaction


@reaction
class DailyOrderLimit(Reaction):
    """At most MAX orders can be paid per day."""
    priority = 10
    MAX = 5

    def fresh(self):
        return {"paid": 0}

    def check(self, svc, order, action):
        if action == "pay" and self.state["paid"] >= self.MAX:
            self.refuse(f"{self.MAX} orders have been paid today")

    def apply(self, svc, order, action):
        if action != "pay":
            return []
        self.state["paid"] += 1
        if self.state["paid"] == self.MAX:
            return [("limit.reached", {"limit": {"day": svc.day.isoformat(), "max": self.MAX}})]
        return []

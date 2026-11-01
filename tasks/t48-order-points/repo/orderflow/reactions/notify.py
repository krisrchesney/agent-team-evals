from .base import Reaction
from .registry import reaction


@reaction
class Notify(Reaction):
    """Queue a notice for the customer after every move. Always last."""
    priority = 90

    def apply(self, svc, order, action):
        notice = {"order": order.id, "customer": order.customer, "status": order.status}
        return [("notice.queued", {"notice": notice})]

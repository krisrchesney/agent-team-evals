"""Save and load a desk as plain data (JSON-friendly): customers, tickets, comments, id counters and the feed."""
from datetime import datetime

from .models import Comment, Customer, Ticket
from .views import stamp


def _when(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def dump(desk):
    store = desk.store
    return {
        "version": 1,
        "ids": dict(desk.ids.counters),
        "customers": [{"id": c.id, "name": c.name, "email": c.email, "created_at": stamp(c.created_at)}
                      for c in store.customers.values()],
        "tickets": [{"id": t.id, "customer": t.customer, "subject": t.subject, "body": t.body,
                     "status": t.status, "priority": t.priority, "tags": list(t.tags),
                     "created_at": stamp(t.created_at), "updated_at": stamp(t.updated_at)}
                    for t in store.tickets.values()],
        "comments": [{"id": m.id, "ticket": m.ticket, "author": m.author, "text": m.text,
                      "created_at": stamp(m.created_at)} for m in store.comments.values()],
        "feed": [dict(e) for e in desk.feed.events],
    }


def load(data, desk):
    """Fill an empty Desk from dumped data and rebuild its search index."""
    desk.ids.counters = dict(data["ids"])
    for c in data["customers"]:
        desk.store.add_customer(Customer(id=c["id"], name=c["name"], email=c["email"],
                                         created_at=_when(c["created_at"])))
    for t in data["tickets"]:
        desk.store.add_ticket(Ticket(id=t["id"], customer=t["customer"], subject=t["subject"], body=t["body"],
                                     status=t["status"], priority=t["priority"], tags=tuple(t["tags"]),
                                     created_at=_when(t["created_at"]), updated_at=_when(t["updated_at"])))
    for m in data["comments"]:
        desk.store.add_comment(Comment(id=m["id"], ticket=m["ticket"], author=m["author"], text=m["text"],
                                       created_at=_when(m["created_at"])))
    desk.feed.events = [dict(e) for e in data["feed"]]
    for ticket_id in desk.store.tickets:
        desk.search.reindex(ticket_id)

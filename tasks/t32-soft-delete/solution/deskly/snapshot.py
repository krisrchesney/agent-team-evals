"""Save and load a desk as plain data (JSON-friendly): every row, deleted or not, the id counters and the feed."""
from datetime import datetime

from .models import Comment, Customer, Ticket
from .views import stamp


def _when(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ") if text else None


def _gone(row):
    return {"deleted_at": stamp(row.deleted_at) if row.deleted_at is not None else None,
            "deleted_with": row.deleted_with}


def dump(desk):
    store = desk.store
    return {
        "version": 2,
        "ids": dict(desk.ids.counters),
        "customers": [{"id": c.id, "name": c.name, "email": c.email, "created_at": stamp(c.created_at),
                       **_gone(c)} for c in store.customers.values()],
        "tickets": [{"id": t.id, "customer": t.customer, "subject": t.subject, "body": t.body,
                     "status": t.status, "priority": t.priority, "tags": list(t.tags),
                     "created_at": stamp(t.created_at), "updated_at": stamp(t.updated_at), **_gone(t)}
                    for t in store.tickets.values()],
        "comments": [{"id": m.id, "ticket": m.ticket, "author": m.author, "text": m.text,
                      "created_at": stamp(m.created_at), **_gone(m)} for m in store.comments.values()],
        "feed": [dict(e) for e in desk.feed.events],
    }


def load(data, desk):
    """Fill an empty Desk from dumped data and rebuild its search index. Older dumps have no deleted rows."""
    desk.ids.counters = dict(data["ids"])
    for c in data["customers"]:
        desk.store.add_customer(Customer(id=c["id"], name=c["name"], email=c["email"],
                                         created_at=_when(c["created_at"]),
                                         deleted_at=_when(c.get("deleted_at")),
                                         deleted_with=c.get("deleted_with")))
    for t in data["tickets"]:
        desk.store.add_ticket(Ticket(id=t["id"], customer=t["customer"], subject=t["subject"], body=t["body"],
                                     status=t["status"], priority=t["priority"], tags=tuple(t["tags"]),
                                     created_at=_when(t["created_at"]), updated_at=_when(t["updated_at"]),
                                     deleted_at=_when(t.get("deleted_at")), deleted_with=t.get("deleted_with")))
    for m in data["comments"]:
        desk.store.add_comment(Comment(id=m["id"], ticket=m["ticket"], author=m["author"], text=m["text"],
                                       created_at=_when(m["created_at"]), deleted_at=_when(m.get("deleted_at")),
                                       deleted_with=m.get("deleted_with")))
    desk.feed.events = [dict(e) for e in data["feed"]]
    for ticket in desk.store.all_tickets():
        desk.search.reindex(ticket.id)

from . import validate
from .models import Ticket
from .views import ticket_view


def open_(desk, customer, subject, body, priority=2, tags=()):
    store = desk.store
    owner = store.customer(customer)
    subject = validate.text(subject, "subject")
    body = validate.text(body, "body", max_len=2000)
    priority = validate.priority(priority)
    tags = validate.tags(tags)
    now = desk.clock.now()
    ticket = Ticket(id=desk.ids.new("t"), customer=owner.id, subject=subject, body=body, status="open",
                    priority=priority, tags=tags, created_at=now, updated_at=now)
    store.add_ticket(ticket)
    desk.search.reindex(ticket.id)
    desk.feed.record("ticket.opened", {"id": ticket.id, "customer": owner.id})
    return ticket_view(store, ticket)


def get(desk, ticket_id):
    return ticket_view(desk.store, desk.store.ticket(ticket_id))


def list_(desk, customer=None, status=None, tag=None, limit=None):
    store = desk.store
    limit = validate.limit(limit)
    if customer is not None:
        found = store.tickets_of(store.customer(customer).id)
    elif tag is not None:
        found = store.tickets_tagged(validate.tag(tag))
    else:
        found = list(store.tickets.values())
    if customer is not None and tag is not None:
        found = [t for t in found if validate.tag(tag) in t.tags]
    if status is not None:
        found = [t for t in found if t.status == validate.status(status)]
    found.sort(key=lambda t: (t.created_at, int(t.id[1:])), reverse=True)
    return {"data": [ticket_view(store, t) for t in found[:limit]], "has_more": len(found) > limit}


def _touch(desk, ticket):
    ticket.updated_at = desk.clock.now()


def set_status(desk, ticket_id, status):
    ticket = desk.store.ticket(ticket_id)
    status = validate.status(status)
    before, ticket.status = ticket.status, status
    _touch(desk, ticket)
    desk.feed.record("ticket.status_changed", {"id": ticket.id, "from": before, "to": status})
    return ticket_view(desk.store, ticket)


def add_tag(desk, ticket_id, tag):
    ticket = desk.store.ticket(ticket_id)
    desk.store.retag(ticket, validate.tags(ticket.tags + (validate.tag(tag),)))
    _touch(desk, ticket)
    desk.feed.record("ticket.tagged", {"id": ticket.id, "tag": validate.tag(tag)})
    return ticket_view(desk.store, ticket)


def remove_tag(desk, ticket_id, tag):
    ticket = desk.store.ticket(ticket_id)
    tag = validate.tag(tag)
    desk.store.retag(ticket, tuple(t for t in ticket.tags if t != tag))
    _touch(desk, ticket)
    desk.feed.record("ticket.untagged", {"id": ticket.id, "tag": tag})
    return ticket_view(desk.store, ticket)


def rename_tag(desk, old, new):
    """Rename a tag on every ticket that has it; returns how many tickets changed."""
    old, new = validate.tag(old), validate.tag(new)
    changed = desk.store.tickets_tagged(old)
    for ticket in changed:
        desk.store.retag(ticket, validate.tags([new if t == old else t for t in ticket.tags]))
    desk.feed.record("tag.renamed", {"from": old, "to": new, "tickets": len(changed)})
    return {"renamed": len(changed)}


def remove(desk, ticket_id):
    """Drop a ticket and its comments from the store and the search index."""
    desk.store.drop_ticket(ticket_id)
    desk.search.drop(ticket_id)


def delete(desk, ticket_id):
    ticket = desk.store.ticket(ticket_id)
    comments = len(desk.store.comments_of(ticket.id))
    remove(desk, ticket.id)
    desk.feed.record("ticket.deleted", {"id": ticket.id, "comments": comments})
    return {"id": ticket.id, "deleted": True}

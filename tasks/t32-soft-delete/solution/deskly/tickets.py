from . import validate
from .errors import Conflict
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


def get(desk, ticket_id, include_deleted=False):
    return ticket_view(desk.store, desk.store.ticket(ticket_id, include_deleted))


def list_(desk, customer=None, status=None, tag=None, limit=None, include_deleted=False):
    store = desk.store
    limit = validate.limit(limit)
    if customer is not None:
        found = store.tickets_of(store.customer(customer, include_deleted).id, include_deleted)
    elif tag is not None:
        found = store.tickets_tagged(validate.tag(tag), include_deleted)
    else:
        found = store.all_tickets(include_deleted)
    if customer is not None and tag is not None:
        found = [t for t in found if validate.tag(tag) in t.tags]
    if status is not None:
        found = [t for t in found if t.status == validate.status(status)]
    found = sorted(found, key=lambda t: (t.created_at, int(t.id[1:])), reverse=True)
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
    """Rename a tag on every ticket that has it, deleted ones too; returns how many live tickets changed."""
    old, new = validate.tag(old), validate.tag(new)
    changed = desk.store.tickets_tagged(old, include_deleted=True)
    for ticket in changed:
        desk.store.retag(ticket, validate.tags([new if t == old else t for t in ticket.tags]))
    live = sum(1 for t in changed if t.deleted_at is None)
    desk.feed.record("tag.renamed", {"from": old, "to": new, "tickets": live})
    return {"renamed": live}


def mark_deleted(desk, ticket, now, ticket_key, comment_key):
    """Soft-delete a live ticket and its live comments; the keys say which delete they belong to."""
    for comment in desk.store.comments_of(ticket.id):
        comment.deleted_at = now
        comment.deleted_with = comment_key
    ticket.deleted_at = now
    ticket.deleted_with = ticket_key
    desk.search.drop(ticket.id)


def unmark_deleted(desk, ticket, key):
    """Undo mark_deleted for a ticket and for the comments that were deleted under the same key."""
    ticket.deleted_at = None
    ticket.deleted_with = None
    for comment in desk.store.comments_of(ticket.id, include_deleted=True):
        if comment.deleted_with == key:
            comment.deleted_at = None
            comment.deleted_with = None
    desk.search.reindex(ticket.id)


def delete(desk, ticket_id):
    ticket = desk.store.ticket(ticket_id)
    comments = len(desk.store.comments_of(ticket.id))
    mark_deleted(desk, ticket, desk.clock.now(), ticket_key=None, comment_key=f"ticket:{ticket.id}")
    desk.feed.record("ticket.deleted", {"id": ticket.id, "comments": comments})
    return ticket_view(desk.store, ticket)


def restore(desk, ticket_id):
    store = desk.store
    ticket = store.ticket(ticket_id, include_deleted=True)
    if ticket.deleted_at is None:
        raise Conflict(f"ticket {ticket.id} is not deleted", param="ticket")
    if store.customer(ticket.customer, include_deleted=True).deleted_at is not None:
        raise Conflict(f"customer {ticket.customer} is deleted", param="customer")
    key = f"ticket:{ticket.id}"
    back = sum(1 for c in store.comments_of(ticket.id, include_deleted=True) if c.deleted_with == key)
    unmark_deleted(desk, ticket, key)
    desk.feed.record("ticket.restored", {"id": ticket.id, "comments": back})
    return ticket_view(store, ticket)

"""The trash: listing deleted rows, restoring is done by each module, and permanent removal."""
from datetime import timedelta

from . import validate
from .errors import Conflict, InvalidInput, NotFound

KINDS = ("customer", "ticket", "comment")
RETENTION = timedelta(days=30)


def _label(kind, row):
    if kind == "customer":
        return row.name
    if kind == "ticket":
        return row.subject
    return row.text[:40]


def _rows(store, kind):
    return {"customer": store.all_customers, "ticket": store.all_tickets, "comment": store.all_comments}[kind](True)


def listing(desk, kind=None, limit=None):
    """Every deleted row, most recently deleted first (ties: customers, tickets, comments, then oldest id)."""
    if kind is not None and kind not in KINDS:
        raise InvalidInput(f"kind must be one of {', '.join(KINDS)}", param="kind")
    limit = validate.limit(limit, default=20)
    rows = [(k, r) for k in KINDS if kind in (None, k) for r in _rows(desk.store, k) if r.deleted_at is not None]
    rows.sort(key=lambda kr: (-kr[1].deleted_at.timestamp(), KINDS.index(kr[0]), int(kr[1].id[1:])))
    return {"data": [{"kind": k, "id": r.id, "label": _label(k, r), "deleted_at": r.deleted_at.strftime(
        "%Y-%m-%dT%H:%M:%SZ")} for k, r in rows[:limit]], "has_more": len(rows) > limit}


def _remove(desk, kind, row):
    """Permanently remove a row and what belongs to it; returns the counts of rows that went."""
    store = desk.store
    gone = {"customers": 0, "tickets": 0, "comments": 0}
    if kind == "customer":
        owned = store.tickets_of(row.id, include_deleted=True)
        gone["customers"] = 1
        gone["tickets"] = len(owned)
        gone["comments"] = sum(len(store.comments_of(t.id, include_deleted=True)) for t in owned)
        for ticket in owned:
            desk.search.drop(ticket.id)
        store.drop_customer(row.id)
    elif kind == "ticket":
        gone["tickets"] = 1
        gone["comments"] = len(store.comments_of(row.id, include_deleted=True))
        desk.search.drop(row.id)
        store.drop_ticket(row.id)
    else:
        gone["comments"] = 1
        store.drop_comment(row.id)
    return gone


def purge(desk, kind, row_id):
    if kind not in KINDS:
        raise InvalidInput(f"kind must be one of {', '.join(KINDS)}", param="kind")
    store = desk.store
    row = getattr(store, kind)(row_id, include_deleted=True)
    if row.deleted_at is None:
        raise Conflict(f"{kind} {row.id} is not deleted", param=kind)
    _remove(desk, kind, row)
    desk.feed.record(f"{kind}.purged", {"id": row_id})
    return {"id": row_id, "purged": True}


def purge_expired(desk):
    """Remove everything deleted more than 30 days ago (exactly 30 days ago stays)."""
    cutoff = desk.clock.now() - RETENTION
    total = {"customers": 0, "tickets": 0, "comments": 0}
    for kind in KINDS:
        for row in [r for r in _rows(desk.store, kind) if r.deleted_at is not None and r.deleted_at < cutoff]:
            for name, n in _remove(desk, kind, row).items():
                total[name] += n
    if any(total.values()):
        desk.feed.record("trash.purged", dict(total))
    return {"purged": total}

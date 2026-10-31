from datetime import timedelta

from . import validate

BUCKETS = (("0-1", 0, 1), ("2-7", 2, 7), ("8-30", 8, 30), ("31+", 31, None))


def status_counts(desk):
    counts = dict.fromkeys(validate.STATUSES, 0)
    for ticket in desk.store.all_tickets():
        counts[ticket.status] += 1
    return counts


def tag_counts(desk):
    counts = {}
    for ticket in desk.store.all_tickets():
        for tag in ticket.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return [{"tag": tag, "count": n} for tag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def customer_summary(desk, customer):
    store = desk.store
    owner = store.customer(customer)
    owned = store.tickets_of(owner.id)
    return {"customer": owner.id, "tickets": len(owned),
            "open": sum(1 for t in owned if t.status != "closed"),
            "comments": sum(len(store.comments_of(t.id)) for t in owned)}


def aging(desk):
    """Open and pending tickets by whole days since they were opened."""
    now = desk.clock.now()
    counts = {name: 0 for name, _, _ in BUCKETS}
    for ticket in desk.store.all_tickets():
        if ticket.status == "closed":
            continue
        days = (now - ticket.created_at) // timedelta(days=1)
        for name, low, high in BUCKETS:
            if days >= low and (high is None or days <= high):
                counts[name] += 1
                break
    return counts


def busiest_customers(desk, limit=3):
    """Customers with the most unclosed tickets (at least one), then by name."""
    counts = {}
    for ticket in desk.store.all_tickets():
        if ticket.status != "closed":
            counts[ticket.customer] = counts.get(ticket.customer, 0) + 1
    rows = [(n, desk.store.customers[c]) for c, n in counts.items()]
    rows.sort(key=lambda r: (-r[0], r[1].name.lower(), r[1].id))
    return [{"customer": c.id, "name": c.name, "open": n} for n, c in rows[:validate.limit(limit)]]


def stats(desk):
    store = desk.store
    live = {"customers": len(store.all_customers()), "tickets": len(store.all_tickets()),
            "comments": len(store.all_comments())}
    deleted = {"customers": len(store.customers) - live["customers"],
               "tickets": len(store.tickets) - live["tickets"],
               "comments": len(store.comments) - live["comments"]}
    return {**live, "deleted": deleted}

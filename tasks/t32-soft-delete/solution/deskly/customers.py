from . import tickets, validate
from .errors import Conflict, InvalidInput, NotFound
from .models import Customer
from .views import customer_view


def create(desk, name, email):
    name = validate.text(name, "name")
    email = validate.email(email)
    if desk.store.customer_id_for_email(email):
        raise Conflict(f"email {email} is already used", param="email")
    customer = Customer(id=desk.ids.new("c"), name=name, email=email, created_at=desk.clock.now())
    desk.store.add_customer(customer)
    desk.feed.record("customer.created", {"id": customer.id})
    return customer_view(desk.store, customer)


def get(desk, customer_id, include_deleted=False):
    return customer_view(desk.store, desk.store.customer(customer_id, include_deleted))


def find_by_email(desk, email):
    found = desk.store.customer_id_for_email(validate.email(email))
    if found is None:
        raise NotFound(f"no customer with email {email}", param="email")
    return get(desk, found)


def list_(desk, limit=None, include_deleted=False):
    limit = validate.limit(limit)
    found = sorted(desk.store.all_customers(include_deleted), key=lambda c: (c.name.lower(), c.id))
    return {"data": [customer_view(desk.store, c) for c in found[:limit]], "has_more": len(found) > limit}


def update(desk, customer_id, name=None, email=None):
    customer = desk.store.customer(customer_id)
    new_name = validate.text(name, "name") if name is not None else customer.name
    new_email = validate.email(email) if email is not None else customer.email
    holder = desk.store.customer_id_for_email(new_email)
    if holder and holder != customer.id:
        raise Conflict(f"email {new_email} is already used", param="email")
    customer.name = new_name
    if new_email != customer.email:
        desk.store.set_email(customer, new_email)
    desk.feed.record("customer.updated", {"id": customer.id})
    return customer_view(desk.store, customer)


def _mark_deleted(desk, customer, now):
    customer.deleted_at = now
    desk.store.unindex_email(customer)


def delete(desk, customer_id):
    """Soft-delete a customer together with their live tickets and those tickets' comments."""
    customer = desk.store.customer(customer_id)
    now = desk.clock.now()
    key = f"customer:{customer.id}"
    owned = desk.store.tickets_of(customer.id)
    for ticket in owned:
        tickets.mark_deleted(desk, ticket, now, ticket_key=key, comment_key=key)
    _mark_deleted(desk, customer, now)
    desk.feed.record("customer.deleted", {"id": customer.id, "tickets": len(owned)})
    return customer_view(desk.store, customer)


def restore(desk, customer_id):
    """Bring a customer back, with the tickets and comments that were deleted along with them."""
    store = desk.store
    customer = store.customer(customer_id, include_deleted=True)
    if customer.deleted_at is None:
        raise Conflict(f"customer {customer.id} is not deleted", param="customer")
    if store.customer_id_for_email(customer.email):
        raise Conflict(f"email {customer.email} is used by another customer", param="email")
    customer.deleted_at = None
    store.index_email(customer)
    key = f"customer:{customer.id}"
    back = [t for t in store.tickets_of(customer.id, include_deleted=True) if t.deleted_with == key]
    for ticket in back:
        tickets.unmark_deleted(desk, ticket, key)
    desk.feed.record("customer.restored", {"id": customer.id, "tickets": len(back)})
    return customer_view(store, customer)


def merge(desk, keep, drop):
    """Move every ticket of `drop` (deleted ones too) to `keep`, then delete `drop`."""
    if keep == drop:
        raise InvalidInput("cannot merge a customer into itself", param="drop")
    target = desk.store.customer(keep)
    source = desk.store.customer(drop)
    moved = desk.store.tickets_of(source.id, include_deleted=True)
    for ticket in moved:
        desk.store.move_ticket(ticket, target.id)
    _mark_deleted(desk, source, desk.clock.now())
    desk.feed.record("customer.merged", {"id": source.id, "into": target.id, "moved": len(moved)})
    return customer_view(desk.store, target)

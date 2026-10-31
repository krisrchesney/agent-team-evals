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


def get(desk, customer_id):
    return customer_view(desk.store, desk.store.customer(customer_id))


def find_by_email(desk, email):
    found = desk.store.customer_id_for_email(validate.email(email))
    if found is None:
        raise NotFound(f"no customer with email {email}", param="email")
    return get(desk, found)


def list_(desk, limit=None):
    limit = validate.limit(limit)
    found = sorted(desk.store.customers.values(), key=lambda c: (c.name.lower(), c.id))
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


def delete(desk, customer_id):
    """Remove a customer together with their tickets and comments."""
    customer = desk.store.customer(customer_id)
    owned = desk.store.tickets_of(customer.id)
    for ticket in owned:
        tickets.remove(desk, ticket.id)
    desk.store.drop_customer(customer.id)
    desk.feed.record("customer.deleted", {"id": customer.id, "tickets": len(owned)})
    return {"id": customer.id, "deleted": True}


def merge(desk, keep, drop):
    """Move every ticket of `drop` to `keep`, then remove `drop`."""
    if keep == drop:
        raise InvalidInput("cannot merge a customer into itself", param="drop")
    target = desk.store.customer(keep)
    source = desk.store.customer(drop)
    moved = desk.store.tickets_of(source.id)
    for ticket in moved:
        desk.store.move_ticket(ticket, target.id)
    desk.store.drop_customer(source.id)
    desk.feed.record("customer.merged", {"id": source.id, "into": target.id, "moved": len(moved)})
    return customer_view(desk.store, target)

from .. import validate
from ..errors import Conflict, InvalidRequest
from ..models import Contact
from ..views import contact_view
from .registry import operation


def _not_merged(contact, param):
    if contact.status == "merged":
        raise Conflict(f"contact {contact.id} was merged into {contact.merged_into}", param=param)


def _digits(phone):
    return "".join(ch for ch in phone if ch.isdigit())


def _union(first, second, key):
    out, seen = list(first), {key(x) for x in first}
    for item in second:
        if key(item) not in seen:
            seen.add(key(item))
            out.append(item)
    return out


@operation("contact.create")
def create(svc, params):
    now = svc.clock.now()
    name = validate.require_str(params, "name")
    emails = validate.str_list(params, "emails", validate.is_email)
    phones = validate.str_list(params, "phones", validate.is_phone)
    company = validate.optional_str(params, "company", "")
    contact = Contact(id=svc.ids.new("contact"), name=name, emails=emails, phones=phones, company=company,
                      created_at=now, updated_at=now)
    svc.store.contacts[contact.id] = contact
    view = contact_view(contact)
    svc.bus.emit("contact.created", {"contact": view})
    return view


@operation("contact.retrieve")
def retrieve(svc, params):
    return contact_view(svc.store.get_contact(validate.require_str(params, "contact")))


@operation("contact.update")
def update(svc, params):
    """Replaces the fields that are given (name, emails, phones, company); the rest stay."""
    now = svc.clock.now()
    contact = svc.store.get_contact(validate.require_str(params, "contact"))
    _not_merged(contact, "contact")
    name = validate.optional_str(params, "name", contact.name)
    emails = validate.str_list(params, "emails", validate.is_email) if "emails" in params else contact.emails
    phones = validate.str_list(params, "phones", validate.is_phone) if "phones" in params else contact.phones
    company = validate.optional_str(params, "company", contact.company)
    contact.name, contact.emails, contact.phones, contact.company = name, emails, phones, company
    svc.store.bump(contact, now)
    view = contact_view(contact)
    svc.bus.emit("contact.updated", {"contact": view})
    return view


@operation("contact.list")
def list_contacts(svc, params):
    limit = validate.limit(params)
    company = validate.optional_str(params, "company", None)
    rows = sorted((c for c in svc.store.contacts.values() if c.status == "active"),
                  key=lambda c: (c.created_at, c.id))
    if company is not None:
        rows = [c for c in rows if c.company.lower() == company.lower()]
    return {"data": [contact_view(c) for c in rows[:limit]], "has_more": len(rows) > limit}


@operation("contact.merge")
def merge(svc, params):
    now = svc.clock.now()
    primary = svc.store.get_contact(validate.require_str(params, "primary"))
    dup = svc.store.get_contact(validate.require_str(params, "duplicate"))
    if primary.id == dup.id:
        raise InvalidRequest("a contact cannot be merged into itself", param="duplicate")
    _not_merged(primary, "primary")
    _not_merged(dup, "duplicate")
    first, second = (dup, primary) if dup.updated_at > primary.updated_at else (primary, dup)
    name, company = first.name or second.name, first.company or second.company
    primary.emails = _union(primary.emails, dup.emails, str.lower)
    primary.phones = _union(primary.phones, dup.phones, _digits)
    primary.name, primary.company = name, company
    for activity in svc.store.activities.values():
        if activity.contact == dup.id:
            activity.contact = primary.id
    dup.status, dup.merged_into = "merged", primary.id
    svc.store.bump(primary, now)
    svc.store.bump(dup, now)
    view, dup_view = contact_view(primary), contact_view(dup)
    svc.bus.emit("contact.merged", {"contact": view, "duplicate": dup_view})
    return view

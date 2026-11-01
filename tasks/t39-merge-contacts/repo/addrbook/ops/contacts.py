from .. import validate
from ..models import Contact
from ..views import contact_view
from .registry import operation


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
    rows = sorted(svc.store.contacts.values(), key=lambda c: (c.created_at, c.id))
    if company is not None:
        rows = [c for c in rows if c.company.lower() == company.lower()]
    return {"data": [contact_view(c) for c in rows[:limit]], "has_more": len(rows) > limit}

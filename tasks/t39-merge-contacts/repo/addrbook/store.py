from .errors import NotFound


class Store:
    def __init__(self):
        self.contacts = {}
        self.activities = {}

    def get_contact(self, contact_id):
        contact = self.contacts.get(contact_id)
        if contact is None:
            raise NotFound(f"no contact {contact_id!r}", param="contact")
        return contact

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def activities_for(self, contact_id):
        rows = [a for a in self.activities.values() if a.contact == contact_id]
        return sorted(rows, key=lambda a: (a.at, a.id))

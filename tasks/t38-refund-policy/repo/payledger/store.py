from .errors import NotFound
from .models import Entry


class Store:
    def __init__(self):
        self.charges = {}
        self.entries = []

    def get_charge(self, charge_id):
        charge = self.charges.get(charge_id)
        if charge is None:
            raise NotFound(f"no charge {charge_id!r}", param="charge")
        return charge

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def add_entry(self, ids, charge, kind, amount, ref, now):
        entry = Entry(id=ids.new("entry"), charge=charge.id, kind=kind, amount=amount, ref=ref, at=now)
        self.entries.append(entry)
        return entry

    def entries_for(self, charge_id):
        return [e for e in self.entries if e.charge == charge_id]

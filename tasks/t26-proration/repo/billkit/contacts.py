"""Contacts: people to email about a customer's account

Every record has an id like `con_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

ROLE_VALUES = ('billing', 'technical', 'owner')


@dataclass
class Contact:
    id: str
    customer: str
    name: str
    email: str
    role: str = 'billing'


FIELDS = ('customer', 'name', 'email', 'role',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown contact field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['name'] = _text(data, 'name', required=True, limit=80)
    out['email'] = _email(data, 'email')
    out['role'] = _choice(data, 'role', ROLE_VALUES, 'billing')
    return out


class ContactRepo(Repository):
    prefix = 'con'
    noun = 'contact'

    def create(self, **data):
        clean = validate(data)
        rec = Contact(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_customer(self, value):
        return [r for r in self.all() if r.customer == value]

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]

    def with_role(self, value):
        if value not in ROLE_VALUES:
            raise ValidationError(f"bad role {value!r}", field='role')
        return [r for r in self.all() if r.role == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Contact(id=record_id, **validate(data))

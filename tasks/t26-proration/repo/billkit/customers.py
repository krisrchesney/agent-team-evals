"""Customers: people and companies that are billed

Every record has an id like `cus_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATUS_VALUES = ('active', 'paused', 'closed')


@dataclass
class Customer:
    id: str
    name: str
    email: str
    region: str = ''
    status: str = 'active'


FIELDS = ('name', 'email', 'region', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown customer field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=80)
    out['email'] = _email(data, 'email')
    out['region'] = _text(data, 'region', required=False, limit=20)
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'active')
    return out


class CustomerRepo(Repository):
    prefix = 'cus'
    noun = 'customer'

    def create(self, **data):
        clean = validate(data)
        rec = Customer(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]

    def find_by_region(self, value):
        return [r for r in self.all() if r.region == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Customer(id=record_id, **validate(data))

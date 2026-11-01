"""Addresses: billing and shipping addresses of a customer

Every record has an id like `adr_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

KIND_VALUES = ('billing', 'shipping')


@dataclass
class Address:
    id: str
    customer: str
    line1: str
    city: str
    country: str
    postcode: str = ''
    kind: str = 'billing'


FIELDS = ('customer', 'line1', 'city', 'country', 'postcode', 'kind',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown address field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['line1'] = _text(data, 'line1', required=True, limit=120)
    out['city'] = _text(data, 'city', required=True, limit=60)
    out['country'] = _text(data, 'country', required=True, limit=2)
    out['postcode'] = _text(data, 'postcode', required=False, limit=16)
    out['kind'] = _choice(data, 'kind', KIND_VALUES, 'billing')
    return out


class AddressRepo(Repository):
    prefix = 'adr'
    noun = 'address'

    def create(self, **data):
        clean = validate(data)
        rec = Address(id=self.next_id(), **clean)
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

    def find_by_line1(self, value):
        return [r for r in self.all() if r.line1 == value]

    def with_kind(self, value):
        if value not in KIND_VALUES:
            raise ValidationError(f"bad kind {value!r}", field='kind')
        return [r for r in self.all() if r.kind == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Address(id=record_id, **validate(data))

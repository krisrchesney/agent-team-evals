"""Vat ids: tax identifiers customers have registered

Every record has an id like `vat_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATUS_VALUES = ('pending', 'valid', 'invalid')


@dataclass
class VatId:
    id: str
    customer: str
    country: str
    number: str
    status: str = 'pending'


FIELDS = ('customer', 'country', 'number', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown vatid field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['country'] = _text(data, 'country', required=True, limit=2)
    out['number'] = _text(data, 'number', required=True, limit=24)
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'pending')
    return out


class VatIdRepo(Repository):
    prefix = 'vat'
    noun = 'vatid'

    def create(self, **data):
        clean = validate(data)
        rec = VatId(id=self.next_id(), **clean)
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

    def find_by_country(self, value):
        return [r for r in self.all() if r.country == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return VatId(id=record_id, **validate(data))

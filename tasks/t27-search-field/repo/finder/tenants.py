"""Tenants: customers of a hosted search service

Every record has an id like `tnt_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

PLAN_VALUES = ('free', 'pro', 'enterprise')


@dataclass
class Tenant:
    id: str
    name: str
    contact: str
    plan: str = 'free'
    seats: int = 1


FIELDS = ('name', 'contact', 'plan', 'seats',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown tenant field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=80)
    out['contact'] = _email(data, 'contact')
    out['plan'] = _choice(data, 'plan', PLAN_VALUES, 'free')
    out['seats'] = _int(data, 'seats', 1, 1000)
    return out


class TenantRepo(Repository):
    prefix = 'tnt'
    noun = 'tenant'

    def create(self, **data):
        clean = validate(data)
        rec = Tenant(id=self.next_id(), **clean)
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

    def with_plan(self, value):
        if value not in PLAN_VALUES:
            raise ValidationError(f"bad plan {value!r}", field='plan')
        return [r for r in self.all() if r.plan == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Tenant(id=record_id, **validate(data))

"""Dimensions: custom dimensions attached to events

Every record has an id like `dim_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

SCOPE_VALUES = ('event', 'session', 'user')


@dataclass
class Dimension:
    id: str
    name: str
    scope: str = 'event'
    active: bool = True


FIELDS = ('name', 'scope', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown dimension field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['scope'] = _choice(data, 'scope', SCOPE_VALUES, 'event')
    out['active'] = bool(data.get('active', True))
    return out


class DimensionRepo(Repository):
    prefix = 'dim'
    noun = 'dimension'

    def create(self, **data):
        clean = validate(data)
        rec = Dimension(id=self.next_id(), **clean)
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

    def with_scope(self, value):
        if value not in SCOPE_VALUES:
            raise ValidationError(f"bad scope {value!r}", field='scope')
        return [r for r in self.all() if r.scope == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Dimension(id=record_id, **validate(data))

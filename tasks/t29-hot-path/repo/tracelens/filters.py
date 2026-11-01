"""Filters: rules that drop or keep events

Every record has an id like `flt_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

FIELD_VALUES = ('page', 'user', 'kind')
ACTION_VALUES = ('drop', 'keep')


@dataclass
class Filter:
    id: str
    name: str
    pattern: str
    field: str = 'page'
    action: str = 'drop'


FIELDS = ('name', 'pattern', 'field', 'action',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown filter field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['pattern'] = _text(data, 'pattern', required=True, limit=120)
    out['field'] = _choice(data, 'field', FIELD_VALUES, 'page')
    out['action'] = _choice(data, 'action', ACTION_VALUES, 'drop')
    return out


class FilterRepo(Repository):
    prefix = 'flt'
    noun = 'filter'

    def create(self, **data):
        clean = validate(data)
        rec = Filter(id=self.next_id(), **clean)
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

    def find_by_pattern(self, value):
        return [r for r in self.all() if r.pattern == value]

    def with_field(self, value):
        if value not in FIELD_VALUES:
            raise ValidationError(f"bad field {value!r}", field='field')
        return [r for r in self.all() if r.field == value]

    def with_action(self, value):
        if value not in ACTION_VALUES:
            raise ValidationError(f"bad action {value!r}", field='action')
        return [r for r in self.all() if r.action == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Filter(id=record_id, **validate(data))

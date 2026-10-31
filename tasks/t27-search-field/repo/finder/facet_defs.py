"""Facet defs: facets shown in the sidebar

Every record has an id like `fct_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

FIELD_VALUES = ('tags', 'title')


@dataclass
class Facet:
    id: str
    name: str
    field: str = 'tags'
    limit: int = 1
    visible: bool = True


FIELDS = ('name', 'field', 'limit', 'visible',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown facet field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['field'] = _choice(data, 'field', FIELD_VALUES, 'tags')
    out['limit'] = _int(data, 'limit', 1, 50)
    out['visible'] = bool(data.get('visible', True))
    return out


class FacetRepo(Repository):
    prefix = 'fct'
    noun = 'facet'

    def create(self, **data):
        clean = validate(data)
        rec = Facet(id=self.next_id(), **clean)
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

    def with_field(self, value):
        if value not in FIELD_VALUES:
            raise ValidationError(f"bad field {value!r}", field='field')
        return [r for r in self.all() if r.field == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Facet(id=record_id, **validate(data))

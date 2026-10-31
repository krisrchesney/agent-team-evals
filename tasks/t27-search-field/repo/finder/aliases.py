"""Aliases: alternate names for collections

Every record has an id like `als_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Alias:
    id: str
    name: str
    target: str
    note: str = ''


FIELDS = ('name', 'target', 'note',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown alias field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['target'] = _text(data, 'target', required=True, limit=64)
    out['note'] = _text(data, 'note', required=False, limit=200)
    return out


class AliasRepo(Repository):
    prefix = 'als'
    noun = 'alias'

    def create(self, **data):
        clean = validate(data)
        rec = Alias(id=self.next_id(), **clean)
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

    def find_by_target(self, value):
        return [r for r in self.all() if r.target == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Alias(id=record_id, **validate(data))

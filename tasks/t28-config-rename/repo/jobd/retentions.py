"""Retentions: how long finished jobs are kept

Every record has an id like `ret_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Retention:
    id: str
    name: str
    days: int = 1
    handler: str = ''
    archive: bool = False


FIELDS = ('name', 'days', 'handler', 'archive',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown retention field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['days'] = _int(data, 'days', 1, 3650)
    out['handler'] = _text(data, 'handler', required=False, limit=60)
    out['archive'] = bool(data.get('archive', False))
    return out


class RetentionRepo(Repository):
    prefix = 'ret'
    noun = 'retention'

    def create(self, **data):
        clean = validate(data)
        rec = Retention(id=self.next_id(), **clean)
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

    def find_by_handler(self, value):
        return [r for r in self.all() if r.handler == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Retention(id=record_id, **validate(data))

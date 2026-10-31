"""Queues: named queues jobs are placed on

Every record has an id like `que_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class QueueDef:
    id: str
    name: str
    description: str = ''
    priority: int = 0
    paused: bool = False


FIELDS = ('name', 'description', 'priority', 'paused',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown queuedef field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['description'] = _text(data, 'description', required=False, limit=200)
    out['priority'] = _int(data, 'priority', 0, 9)
    out['paused'] = bool(data.get('paused', False))
    return out


class QueueDefRepo(Repository):
    prefix = 'que'
    noun = 'queuedef'

    def create(self, **data):
        clean = validate(data)
        rec = QueueDef(id=self.next_id(), **clean)
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

    def find_by_description(self, value):
        return [r for r in self.all() if r.description == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return QueueDef(id=record_id, **validate(data))

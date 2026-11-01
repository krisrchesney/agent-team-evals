"""Windows: maintenance windows when schedules pause

Every record has an id like `win_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Window:
    id: str
    name: str
    starts: str
    ends: str
    recurring: bool = False


FIELDS = ('name', 'starts', 'ends', 'recurring',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown window field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['starts'] = _text(data, 'starts', required=True, limit=20)
    out['ends'] = _text(data, 'ends', required=True, limit=20)
    out['recurring'] = bool(data.get('recurring', False))
    return out


class WindowRepo(Repository):
    prefix = 'win'
    noun = 'window'

    def create(self, **data):
        clean = validate(data)
        rec = Window(id=self.next_id(), **clean)
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

    def find_by_starts(self, value):
        return [r for r in self.all() if r.starts == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Window(id=record_id, **validate(data))

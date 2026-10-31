"""Goals: conversions we count

Every record has an id like `gol_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Goal:
    id: str
    name: str
    page: str
    value_cents: int = 0
    active: bool = True


FIELDS = ('name', 'page', 'value_cents', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown goal field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['page'] = _text(data, 'page', required=True, limit=200)
    out['value_cents'] = _int(data, 'value_cents', 0, 100000000)
    out['active'] = bool(data.get('active', True))
    return out


class GoalRepo(Repository):
    prefix = 'gol'
    noun = 'goal'

    def create(self, **data):
        clean = validate(data)
        rec = Goal(id=self.next_id(), **clean)
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

    def find_by_page(self, value):
        return [r for r in self.all() if r.page == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Goal(id=record_id, **validate(data))

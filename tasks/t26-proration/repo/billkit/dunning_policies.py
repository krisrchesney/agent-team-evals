"""Dunning policies: how aggressively unpaid invoices are chased

Every record has an id like `dun_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

TONE_VALUES = ('friendly', 'firm', 'final')


@dataclass
class DunningPolicy:
    id: str
    name: str
    max_attempts: int = 1
    tone: str = 'friendly'


FIELDS = ('name', 'max_attempts', 'tone',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown dunningpolicy field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['max_attempts'] = _int(data, 'max_attempts', 1, 10)
    out['tone'] = _choice(data, 'tone', TONE_VALUES, 'friendly')
    return out


class DunningPolicyRepo(Repository):
    prefix = 'dun'
    noun = 'dunningpolicy'

    def create(self, **data):
        clean = validate(data)
        rec = DunningPolicy(id=self.next_id(), **clean)
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

    def with_tone(self, value):
        if value not in TONE_VALUES:
            raise ValidationError(f"bad tone {value!r}", field='tone')
        return [r for r in self.all() if r.tone == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return DunningPolicy(id=record_id, **validate(data))

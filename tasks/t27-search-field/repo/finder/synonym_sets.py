"""Synonym sets: groups of words that mean the same

Every record has an id like `syn_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

DIRECTION_VALUES = ('both', 'one_way')


@dataclass
class SynonymSet:
    id: str
    name: str
    words: str
    direction: str = 'both'


FIELDS = ('name', 'words', 'direction',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown synonymset field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['words'] = _text(data, 'words', required=True, limit=300)
    out['direction'] = _choice(data, 'direction', DIRECTION_VALUES, 'both')
    return out


class SynonymSetRepo(Repository):
    prefix = 'syn'
    noun = 'synonymset'

    def create(self, **data):
        clean = validate(data)
        rec = SynonymSet(id=self.next_id(), **clean)
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

    def find_by_words(self, value):
        return [r for r in self.all() if r.words == value]

    def with_direction(self, value):
        if value not in DIRECTION_VALUES:
            raise ValidationError(f"bad direction {value!r}", field='direction')
        return [r for r in self.all() if r.direction == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return SynonymSet(id=record_id, **validate(data))

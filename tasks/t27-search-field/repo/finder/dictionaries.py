"""Dictionaries: word lists used by suggestions

Every record has an id like `dic_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATUS_VALUES = ('draft', 'ready', 'stale')


@dataclass
class Dictionary:
    id: str
    name: str
    source: str
    words: int = 0
    status: str = 'draft'


FIELDS = ('name', 'source', 'words', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown dictionary field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['source'] = _text(data, 'source', required=True, limit=200)
    out['words'] = _int(data, 'words', 0, 1000000)
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'draft')
    return out


class DictionaryRepo(Repository):
    prefix = 'dic'
    noun = 'dictionary'

    def create(self, **data):
        clean = validate(data)
        rec = Dictionary(id=self.next_id(), **clean)
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

    def find_by_source(self, value):
        return [r for r in self.all() if r.source == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Dictionary(id=record_id, **validate(data))

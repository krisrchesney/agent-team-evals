"""Notes: free-text notes support staff attach to customers

Every record has an id like `nte_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Note:
    id: str
    customer: str
    body: str
    author: str = ''


FIELDS = ('customer', 'body', 'author',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown note field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['body'] = _text(data, 'body', required=True, limit=1000)
    out['author'] = _text(data, 'author', required=False, limit=60)
    return out


class NoteRepo(Repository):
    prefix = 'nte'
    noun = 'note'

    def create(self, **data):
        clean = validate(data)
        rec = Note(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_customer(self, value):
        return [r for r in self.all() if r.customer == value]

    def find_by_body(self, value):
        return [r for r in self.all() if r.body == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Note(id=record_id, **validate(data))

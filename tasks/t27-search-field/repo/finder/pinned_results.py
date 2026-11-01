"""Pinned results: documents promoted for a query

Every record has an id like `pin_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class PinnedResult:
    id: str
    query: str
    doc: str
    position: int = 1
    active: bool = True


FIELDS = ('query', 'doc', 'position', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown pinnedresult field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['query'] = _text(data, 'query', required=True, limit=200)
    out['doc'] = _text(data, 'doc', required=True, limit=64)
    out['position'] = _int(data, 'position', 1, 20)
    out['active'] = bool(data.get('active', True))
    return out


class PinnedResultRepo(Repository):
    prefix = 'pin'
    noun = 'pinnedresult'

    def create(self, **data):
        clean = validate(data)
        rec = PinnedResult(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_query(self, value):
        return [r for r in self.all() if r.query == value]

    def find_by_doc(self, value):
        return [r for r in self.all() if r.doc == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return PinnedResult(id=record_id, **validate(data))

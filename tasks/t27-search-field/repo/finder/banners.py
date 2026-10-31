"""Banners: messages shown above results for a query

Every record has an id like `ban_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Banner:
    id: str
    query: str
    message: str
    starts: str = ''
    ends: str = ''


FIELDS = ('query', 'message', 'starts', 'ends',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown banner field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['query'] = _text(data, 'query', required=True, limit=200)
    out['message'] = _text(data, 'message', required=True, limit=300)
    out['starts'] = _text(data, 'starts', required=False, limit=20)
    out['ends'] = _text(data, 'ends', required=False, limit=20)
    return out


class BannerRepo(Repository):
    prefix = 'ban'
    noun = 'banner'

    def create(self, **data):
        clean = validate(data)
        rec = Banner(id=self.next_id(), **clean)
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

    def find_by_message(self, value):
        return [r for r in self.all() if r.message == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Banner(id=record_id, **validate(data))

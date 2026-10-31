"""Annotations: notes pinned to dates on charts

Every record has an id like `ann_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Annotation:
    id: str
    site: str
    day: str
    text: str
    author: str = ''


FIELDS = ('site', 'day', 'text', 'author',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown annotation field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['site'] = _text(data, 'site', required=True, limit=80)
    out['day'] = _text(data, 'day', required=True, limit=10)
    out['text'] = _text(data, 'text', required=True, limit=200)
    out['author'] = _text(data, 'author', required=False, limit=60)
    return out


class AnnotationRepo(Repository):
    prefix = 'ann'
    noun = 'annotation'

    def create(self, **data):
        clean = validate(data)
        rec = Annotation(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_site(self, value):
        return [r for r in self.all() if r.site == value]

    def find_by_day(self, value):
        return [r for r in self.all() if r.day == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Annotation(id=record_id, **validate(data))

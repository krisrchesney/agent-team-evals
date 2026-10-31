"""Segments: saved groups of users

Every record has an id like `seg_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Segment:
    id: str
    name: str
    rule: str
    owner: str = ''
    shared: bool = False


FIELDS = ('name', 'rule', 'owner', 'shared',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown segment field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['rule'] = _text(data, 'rule', required=True, limit=300)
    out['owner'] = _text(data, 'owner', required=False, limit=60)
    out['shared'] = bool(data.get('shared', False))
    return out


class SegmentRepo(Repository):
    prefix = 'seg'
    noun = 'segment'

    def create(self, **data):
        clean = validate(data)
        rec = Segment(id=self.next_id(), **clean)
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

    def find_by_rule(self, value):
        return [r for r in self.all() if r.rule == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Segment(id=record_id, **validate(data))

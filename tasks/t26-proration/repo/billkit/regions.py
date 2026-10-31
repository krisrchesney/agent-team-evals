"""Regions: sales regions

Every record has an id like `reg_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Region:
    id: str
    code: str
    name: str
    currency: str
    active: bool = True


FIELDS = ('code', 'name', 'currency', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown region field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['code'] = _text(data, 'code', required=True, limit=12)
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['currency'] = _text(data, 'currency', required=True, limit=3)
    out['active'] = bool(data.get('active', True))
    return out


class RegionRepo(Repository):
    prefix = 'reg'
    noun = 'region'

    def create(self, **data):
        clean = validate(data)
        rec = Region(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_code(self, value):
        return [r for r in self.all() if r.code == value]

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Region(id=record_id, **validate(data))

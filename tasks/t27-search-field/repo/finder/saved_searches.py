"""Saved searches: queries users keep

Every record has an id like `sav_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class SavedSearch:
    id: str
    owner: str
    name: str
    query: str
    notify: bool = False


FIELDS = ('owner', 'name', 'query', 'notify',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown savedsearch field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['owner'] = _text(data, 'owner', required=True, limit=80)
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['query'] = _text(data, 'query', required=True, limit=300)
    out['notify'] = bool(data.get('notify', False))
    return out


class SavedSearchRepo(Repository):
    prefix = 'sav'
    noun = 'savedsearch'

    def create(self, **data):
        clean = validate(data)
        rec = SavedSearch(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_owner(self, value):
        return [r for r in self.all() if r.owner == value]

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return SavedSearch(id=record_id, **validate(data))

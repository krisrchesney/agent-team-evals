"""Collections: named groups of documents that are searched together

Every record has an id like `col_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

VISIBILITY_VALUES = ('private', 'team', 'public')


@dataclass
class Collection:
    id: str
    name: str
    description: str = ''
    visibility: str = 'private'


FIELDS = ('name', 'description', 'visibility',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown collection field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['description'] = _text(data, 'description', required=False, limit=300)
    out['visibility'] = _choice(data, 'visibility', VISIBILITY_VALUES, 'private')
    return out


class CollectionRepo(Repository):
    prefix = 'col'
    noun = 'collection'

    def create(self, **data):
        clean = validate(data)
        rec = Collection(id=self.next_id(), **clean)
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

    def find_by_description(self, value):
        return [r for r in self.all() if r.description == value]

    def with_visibility(self, value):
        if value not in VISIBILITY_VALUES:
            raise ValidationError(f"bad visibility {value!r}", field='visibility')
        return [r for r in self.all() if r.visibility == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Collection(id=record_id, **validate(data))

"""Api tokens: tokens that may call the search API

Every record has an id like `tok_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

SCOPE_VALUES = ('search', 'index', 'admin')


@dataclass
class ApiToken:
    id: str
    owner: str
    label: str
    scope: str = 'search'
    active: bool = True


FIELDS = ('owner', 'label', 'scope', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown apitoken field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['owner'] = _text(data, 'owner', required=True, limit=80)
    out['label'] = _text(data, 'label', required=True, limit=60)
    out['scope'] = _choice(data, 'scope', SCOPE_VALUES, 'search')
    out['active'] = bool(data.get('active', True))
    return out


class ApiTokenRepo(Repository):
    prefix = 'tok'
    noun = 'apitoken'

    def create(self, **data):
        clean = validate(data)
        rec = ApiToken(id=self.next_id(), **clean)
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

    def find_by_label(self, value):
        return [r for r in self.all() if r.label == value]

    def with_scope(self, value):
        if value not in SCOPE_VALUES:
            raise ValidationError(f"bad scope {value!r}", field='scope')
        return [r for r in self.all() if r.scope == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return ApiToken(id=record_id, **validate(data))

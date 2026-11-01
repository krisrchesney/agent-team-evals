"""Api keys: keys used by integrations

Every record has an id like `key_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

SCOPE_VALUES = ('read', 'write', 'admin')


@dataclass
class ApiKey:
    id: str
    name: str
    hint: str
    scope: str = 'read'


FIELDS = ('name', 'hint', 'scope',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown apikey field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['hint'] = _text(data, 'hint', required=True, limit=8)
    out['scope'] = _choice(data, 'scope', SCOPE_VALUES, 'read')
    return out


class ApiKeyRepo(Repository):
    prefix = 'key'
    noun = 'apikey'

    def create(self, **data):
        clean = validate(data)
        rec = ApiKey(id=self.next_id(), **clean)
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

    def find_by_hint(self, value):
        return [r for r in self.all() if r.hint == value]

    def with_scope(self, value):
        if value not in SCOPE_VALUES:
            raise ValidationError(f"bad scope {value!r}", field='scope')
        return [r for r in self.all() if r.scope == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return ApiKey(id=record_id, **validate(data))

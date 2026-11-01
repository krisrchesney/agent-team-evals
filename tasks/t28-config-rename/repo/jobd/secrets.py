"""Secrets: named secrets handlers may read

Every record has an id like `sec_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Secret:
    id: str
    name: str
    namespace: str
    version: int = 1
    rotated: str = ''


FIELDS = ('name', 'namespace', 'version', 'rotated',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown secret field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['namespace'] = _text(data, 'namespace', required=True, limit=80)
    out['version'] = _int(data, 'version', 1, 1000)
    out['rotated'] = _text(data, 'rotated', required=False, limit=20)
    return out


class SecretRepo(Repository):
    prefix = 'sec'
    noun = 'secret'

    def create(self, **data):
        clean = validate(data)
        rec = Secret(id=self.next_id(), **clean)
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

    def find_by_namespace(self, value):
        return [r for r in self.all() if r.namespace == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Secret(id=record_id, **validate(data))

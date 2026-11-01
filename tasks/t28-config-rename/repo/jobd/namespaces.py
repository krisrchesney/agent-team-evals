"""Namespaces: isolation boundary for queues and handlers

Every record has an id like `nsp_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Namespace:
    id: str
    name: str
    owner: str
    quota_jobs: int = 0
    active: bool = True


FIELDS = ('name', 'owner', 'quota_jobs', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown namespace field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['owner'] = _text(data, 'owner', required=True, limit=80)
    out['quota_jobs'] = _int(data, 'quota_jobs', 0, 10000000)
    out['active'] = bool(data.get('active', True))
    return out


class NamespaceRepo(Repository):
    prefix = 'nsp'
    noun = 'namespace'

    def create(self, **data):
        clean = validate(data)
        rec = Namespace(id=self.next_id(), **clean)
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

    def find_by_owner(self, value):
        return [r for r in self.all() if r.owner == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Namespace(id=record_id, **validate(data))

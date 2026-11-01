"""Handlers: registered job handlers and their limits

Every record has an id like `hnd_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class HandlerDef:
    id: str
    name: str
    module: str
    timeout_s: int = 1
    idempotent: bool = False


FIELDS = ('name', 'module', 'timeout_s', 'idempotent',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown handlerdef field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['module'] = _text(data, 'module', required=True, limit=120)
    out['timeout_s'] = _int(data, 'timeout_s', 1, 86400)
    out['idempotent'] = bool(data.get('idempotent', False))
    return out


class HandlerDefRepo(Repository):
    prefix = 'hnd'
    noun = 'handlerdef'

    def create(self, **data):
        clean = validate(data)
        rec = HandlerDef(id=self.next_id(), **clean)
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

    def find_by_module(self, value):
        return [r for r in self.all() if r.module == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return HandlerDef(id=record_id, **validate(data))

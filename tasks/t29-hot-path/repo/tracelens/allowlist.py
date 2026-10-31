"""Allowlist: hosts allowed to send events

Every record has an id like `alw_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Allowed:
    id: str
    host: str
    site: str = ''
    reason: str = ''


FIELDS = ('host', 'site', 'reason',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown allowed field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['host'] = _text(data, 'host', required=True, limit=120)
    out['site'] = _text(data, 'site', required=False, limit=64)
    out['reason'] = _text(data, 'reason', required=False, limit=200)
    return out


class AllowedRepo(Repository):
    prefix = 'alw'
    noun = 'allowed'

    def create(self, **data):
        clean = validate(data)
        rec = Allowed(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_host(self, value):
        return [r for r in self.all() if r.host == value]

    def find_by_site(self, value):
        return [r for r in self.all() if r.site == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Allowed(id=record_id, **validate(data))

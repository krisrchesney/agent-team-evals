"""Samplings: how much traffic is stored

Every record has an id like `smp_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Sampling:
    id: str
    site: str
    percent: int = 1
    reason: str = ''
    active: bool = True


FIELDS = ('site', 'percent', 'reason', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown sampling field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['site'] = _text(data, 'site', required=True, limit=80)
    out['percent'] = _int(data, 'percent', 1, 100)
    out['reason'] = _text(data, 'reason', required=False, limit=120)
    out['active'] = bool(data.get('active', True))
    return out


class SamplingRepo(Repository):
    prefix = 'smp'
    noun = 'sampling'

    def create(self, **data):
        clean = validate(data)
        rec = Sampling(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_site(self, value):
        return [r for r in self.all() if r.site == value]

    def find_by_reason(self, value):
        return [r for r in self.all() if r.reason == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Sampling(id=record_id, **validate(data))

"""Quotas: limits per namespace

Every record has an id like `quo_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Quota:
    id: str
    namespace: str
    jobs_per_day: int = 0
    burst: int = 0
    hard: bool = False


FIELDS = ('namespace', 'jobs_per_day', 'burst', 'hard',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown quota field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['namespace'] = _text(data, 'namespace', required=True, limit=80)
    out['jobs_per_day'] = _int(data, 'jobs_per_day', 0, 100000000)
    out['burst'] = _int(data, 'burst', 0, 100000)
    out['hard'] = bool(data.get('hard', False))
    return out


class QuotaRepo(Repository):
    prefix = 'quo'
    noun = 'quota'

    def create(self, **data):
        clean = validate(data)
        rec = Quota(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_namespace(self, value):
        return [r for r in self.all() if r.namespace == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Quota(id=record_id, **validate(data))

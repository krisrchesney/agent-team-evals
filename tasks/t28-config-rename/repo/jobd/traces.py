"""Traces: sampled traces of job runs

Every record has an id like `trc_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Trace:
    id: str
    job: str
    span_count: int = 0
    slowest_ms: int = 0
    sampled: bool = True


FIELDS = ('job', 'span_count', 'slowest_ms', 'sampled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown trace field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['job'] = _text(data, 'job', required=True, limit=80)
    out['span_count'] = _int(data, 'span_count', 0, 100000)
    out['slowest_ms'] = _int(data, 'slowest_ms', 0, 86400000)
    out['sampled'] = bool(data.get('sampled', True))
    return out


class TraceRepo(Repository):
    prefix = 'trc'
    noun = 'trace'

    def create(self, **data):
        clean = validate(data)
        rec = Trace(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_job(self, value):
        return [r for r in self.all() if r.job == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Trace(id=record_id, **validate(data))

"""Silences: temporary mutes for alerts

Every record has an id like `sil_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Silence:
    id: str
    alert: str
    reason: str
    until: str
    creator: str = ''


FIELDS = ('alert', 'reason', 'until', 'creator',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown silence field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['alert'] = _text(data, 'alert', required=True, limit=80)
    out['reason'] = _text(data, 'reason', required=True, limit=200)
    out['until'] = _text(data, 'until', required=True, limit=20)
    out['creator'] = _text(data, 'creator', required=False, limit=60)
    return out


class SilenceRepo(Repository):
    prefix = 'sil'
    noun = 'silence'

    def create(self, **data):
        clean = validate(data)
        rec = Silence(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_alert(self, value):
        return [r for r in self.all() if r.alert == value]

    def find_by_reason(self, value):
        return [r for r in self.all() if r.reason == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Silence(id=record_id, **validate(data))

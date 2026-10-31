"""Quotas: monthly event limits

Every record has an id like `quo_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Quota:
    id: str
    site: str
    events: int = 0
    overage_ok: bool = False
    note: str = ''


FIELDS = ('site', 'events', 'overage_ok', 'note',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown quota field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['site'] = _text(data, 'site', required=True, limit=80)
    out['events'] = _int(data, 'events', 0, 1000000000)
    out['overage_ok'] = bool(data.get('overage_ok', False))
    out['note'] = _text(data, 'note', required=False, limit=120)
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

    def find_by_site(self, value):
        return [r for r in self.all() if r.site == value]

    def find_by_note(self, value):
        return [r for r in self.all() if r.note == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Quota(id=record_id, **validate(data))

"""Schedules: recurring reindex jobs

Every record has an id like `sch_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Schedule:
    id: str
    name: str
    cron: str
    collection: str
    enabled: bool = True


FIELDS = ('name', 'cron', 'collection', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown schedule field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['cron'] = _text(data, 'cron', required=True, limit=60)
    out['collection'] = _text(data, 'collection', required=True, limit=80)
    out['enabled'] = bool(data.get('enabled', True))
    return out


class ScheduleRepo(Repository):
    prefix = 'sch'
    noun = 'schedule'

    def create(self, **data):
        clean = validate(data)
        rec = Schedule(id=self.next_id(), **clean)
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

    def find_by_cron(self, value):
        return [r for r in self.all() if r.cron == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Schedule(id=record_id, **validate(data))

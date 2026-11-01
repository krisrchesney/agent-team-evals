"""Schedules: recurring jobs

Every record has an id like `sch_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class ScheduleDef:
    id: str
    name: str
    cron: str
    handler: str
    enabled: bool = True


FIELDS = ('name', 'cron', 'handler', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown scheduledef field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['cron'] = _text(data, 'cron', required=True, limit=60)
    out['handler'] = _text(data, 'handler', required=True, limit=60)
    out['enabled'] = bool(data.get('enabled', True))
    return out


class ScheduleDefRepo(Repository):
    prefix = 'sch'
    noun = 'scheduledef'

    def create(self, **data):
        clean = validate(data)
        rec = ScheduleDef(id=self.next_id(), **clean)
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
    return ScheduleDef(id=record_id, **validate(data))

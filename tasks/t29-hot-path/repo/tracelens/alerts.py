"""Alerts: alerts on traffic

Every record has an id like `alt_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

METRIC_VALUES = ('views', 'sessions', 'errors')


@dataclass
class Alert:
    id: str
    name: str
    metric: str = 'views'
    threshold: int = 0
    enabled: bool = True


FIELDS = ('name', 'metric', 'threshold', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown alert field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['metric'] = _choice(data, 'metric', METRIC_VALUES, 'views')
    out['threshold'] = _int(data, 'threshold', 0, 100000000)
    out['enabled'] = bool(data.get('enabled', True))
    return out


class AlertRepo(Repository):
    prefix = 'alt'
    noun = 'alert'

    def create(self, **data):
        clean = validate(data)
        rec = Alert(id=self.next_id(), **clean)
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

    def with_metric(self, value):
        if value not in METRIC_VALUES:
            raise ValidationError(f"bad metric {value!r}", field='metric')
        return [r for r in self.all() if r.metric == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Alert(id=record_id, **validate(data))

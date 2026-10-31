"""Cohorts: users grouped by first visit

Every record has an id like `coh_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

PERIOD_VALUES = ('day', 'week', 'month')


@dataclass
class Cohort:
    id: str
    name: str
    period: str = 'week'
    size: int = 0


FIELDS = ('name', 'period', 'size',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown cohort field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['period'] = _choice(data, 'period', PERIOD_VALUES, 'week')
    out['size'] = _int(data, 'size', 0, 100000000)
    return out


class CohortRepo(Repository):
    prefix = 'coh'
    noun = 'cohort'

    def create(self, **data):
        clean = validate(data)
        rec = Cohort(id=self.next_id(), **clean)
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

    def with_period(self, value):
        if value not in PERIOD_VALUES:
            raise ValidationError(f"bad period {value!r}", field='period')
        return [r for r in self.all() if r.period == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Cohort(id=record_id, **validate(data))

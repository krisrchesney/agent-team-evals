"""Metrics: custom metrics computed from events

Every record has an id like `met_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Metric:
    id: str
    name: str
    formula: str
    unit: str = ''
    decimals: int = 0


FIELDS = ('name', 'formula', 'unit', 'decimals',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown metric field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['formula'] = _text(data, 'formula', required=True, limit=200)
    out['unit'] = _text(data, 'unit', required=False, limit=20)
    out['decimals'] = _int(data, 'decimals', 0, 6)
    return out


class MetricRepo(Repository):
    prefix = 'met'
    noun = 'metric'

    def create(self, **data):
        clean = validate(data)
        rec = Metric(id=self.next_id(), **clean)
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

    def find_by_formula(self, value):
        return [r for r in self.all() if r.formula == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Metric(id=record_id, **validate(data))

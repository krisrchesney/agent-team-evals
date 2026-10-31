"""Variants: arms of an experiment

Every record has an id like `var_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Variant:
    id: str
    experiment: str
    name: str
    weight: int = 0
    control: bool = False


FIELDS = ('experiment', 'name', 'weight', 'control',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown variant field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['experiment'] = _text(data, 'experiment', required=True, limit=80)
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['weight'] = _int(data, 'weight', 0, 100)
    out['control'] = bool(data.get('control', False))
    return out


class VariantRepo(Repository):
    prefix = 'var'
    noun = 'variant'

    def create(self, **data):
        clean = validate(data)
        rec = Variant(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_experiment(self, value):
        return [r for r in self.all() if r.experiment == value]

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Variant(id=record_id, **validate(data))

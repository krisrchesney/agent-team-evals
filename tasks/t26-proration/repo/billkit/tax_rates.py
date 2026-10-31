"""Tax rates: tax rates by region, in basis points

Every record has an id like `tax_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class TaxRate:
    id: str
    region: str
    label: str
    bps: int = 0
    inclusive: bool = False


FIELDS = ('region', 'label', 'bps', 'inclusive',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown taxrate field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['region'] = _text(data, 'region', required=True, limit=20)
    out['label'] = _text(data, 'label', required=True, limit=40)
    out['bps'] = _int(data, 'bps', 0, 3000)
    out['inclusive'] = bool(data.get('inclusive', False))
    return out


class TaxRateRepo(Repository):
    prefix = 'tax'
    noun = 'taxrate'

    def create(self, **data):
        clean = validate(data)
        rec = TaxRate(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_region(self, value):
        return [r for r in self.all() if r.region == value]

    def find_by_label(self, value):
        return [r for r in self.all() if r.label == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return TaxRate(id=record_id, **validate(data))

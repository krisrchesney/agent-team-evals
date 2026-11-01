"""Discount rules: automatic discounts for large accounts

Every record has an id like `dsr_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class DiscountRule:
    id: str
    name: str
    min_seats: int = 1
    percent: int = 1
    active: bool = True


FIELDS = ('name', 'min_seats', 'percent', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown discountrule field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['min_seats'] = _int(data, 'min_seats', 1, 5000)
    out['percent'] = _int(data, 'percent', 1, 90)
    out['active'] = bool(data.get('active', True))
    return out


class DiscountRuleRepo(Repository):
    prefix = 'dsr'
    noun = 'discountrule'

    def create(self, **data):
        clean = validate(data)
        rec = DiscountRule(id=self.next_id(), **clean)
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


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return DiscountRule(id=record_id, **validate(data))

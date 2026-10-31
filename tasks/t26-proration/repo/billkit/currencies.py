"""Currencies: currencies the books can show

Every record has an id like `cur_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Currency:
    id: str
    code: str
    symbol: str
    decimals: int = 0
    enabled: bool = True


FIELDS = ('code', 'symbol', 'decimals', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown currency field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['code'] = _text(data, 'code', required=True, limit=3)
    out['symbol'] = _text(data, 'symbol', required=True, limit=4)
    out['decimals'] = _int(data, 'decimals', 0, 3)
    out['enabled'] = bool(data.get('enabled', True))
    return out


class CurrencyRepo(Repository):
    prefix = 'cur'
    noun = 'currency'

    def create(self, **data):
        clean = validate(data)
        rec = Currency(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_code(self, value):
        return [r for r in self.all() if r.code == value]

    def find_by_symbol(self, value):
        return [r for r in self.all() if r.symbol == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Currency(id=record_id, **validate(data))

"""Price books: named sets of prices for a currency

Every record has an id like `pbk_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

CURRENCY_VALUES = ('usd', 'eur', 'gbp')
STATUS_VALUES = ('draft', 'live', 'retired')


@dataclass
class PriceBook:
    id: str
    name: str
    currency: str = 'usd'
    status: str = 'draft'


FIELDS = ('name', 'currency', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown pricebook field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['currency'] = _choice(data, 'currency', CURRENCY_VALUES, 'usd')
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'draft')
    return out


class PriceBookRepo(Repository):
    prefix = 'pbk'
    noun = 'pricebook'

    def create(self, **data):
        clean = validate(data)
        rec = PriceBook(id=self.next_id(), **clean)
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

    def with_currency(self, value):
        if value not in CURRENCY_VALUES:
            raise ValidationError(f"bad currency {value!r}", field='currency')
        return [r for r in self.all() if r.currency == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return PriceBook(id=record_id, **validate(data))

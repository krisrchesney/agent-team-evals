"""Payment methods: stored payment methods

Every record has an id like `pm_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

KIND_VALUES = ('card', 'bank', 'wallet')


@dataclass
class PaymentMethod:
    id: str
    customer: str
    last4: str
    kind: str = 'card'
    is_default: bool = False


FIELDS = ('customer', 'last4', 'kind', 'is_default',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown paymentmethod field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['last4'] = _text(data, 'last4', required=True, limit=4)
    out['kind'] = _choice(data, 'kind', KIND_VALUES, 'card')
    out['is_default'] = bool(data.get('is_default', False))
    return out


class PaymentMethodRepo(Repository):
    prefix = 'pm'
    noun = 'paymentmethod'

    def create(self, **data):
        clean = validate(data)
        rec = PaymentMethod(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_customer(self, value):
        return [r for r in self.all() if r.customer == value]

    def find_by_last4(self, value):
        return [r for r in self.all() if r.last4 == value]

    def with_kind(self, value):
        if value not in KIND_VALUES:
            raise ValidationError(f"bad kind {value!r}", field='kind')
        return [r for r in self.all() if r.kind == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return PaymentMethod(id=record_id, **validate(data))

"""Credit reasons: why a credit note was issued

Every record has an id like `crr_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

CATEGORY_VALUES = ('goodwill', 'billing_error', 'cancellation')


@dataclass
class CreditReason:
    id: str
    code: str
    label: str
    category: str = 'goodwill'


FIELDS = ('code', 'label', 'category',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown creditreason field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['code'] = _text(data, 'code', required=True, limit=24)
    out['label'] = _text(data, 'label', required=True, limit=60)
    out['category'] = _choice(data, 'category', CATEGORY_VALUES, 'goodwill')
    return out


class CreditReasonRepo(Repository):
    prefix = 'crr'
    noun = 'creditreason'

    def create(self, **data):
        clean = validate(data)
        rec = CreditReason(id=self.next_id(), **clean)
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

    def find_by_label(self, value):
        return [r for r in self.all() if r.label == value]

    def with_category(self, value):
        if value not in CATEGORY_VALUES:
            raise ValidationError(f"bad category {value!r}", field='category')
        return [r for r in self.all() if r.category == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return CreditReason(id=record_id, **validate(data))

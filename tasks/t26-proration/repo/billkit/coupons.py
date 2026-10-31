"""Coupons: percentage discounts that can be redeemed

Every record has an id like `cpn_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

DURATION_VALUES = ('once', 'repeating', 'forever')


@dataclass
class Coupon:
    id: str
    code: str
    percent: int = 1
    duration: str = 'once'
    max_redemptions: int = 0


FIELDS = ('code', 'percent', 'duration', 'max_redemptions',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown coupon field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['code'] = _text(data, 'code', required=True, limit=32)
    out['percent'] = _int(data, 'percent', 1, 100)
    out['duration'] = _choice(data, 'duration', DURATION_VALUES, 'once')
    out['max_redemptions'] = _int(data, 'max_redemptions', 0, 100000)
    return out


class CouponRepo(Repository):
    prefix = 'cpn'
    noun = 'coupon'

    def create(self, **data):
        clean = validate(data)
        rec = Coupon(id=self.next_id(), **clean)
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

    def with_duration(self, value):
        if value not in DURATION_VALUES:
            raise ValidationError(f"bad duration {value!r}", field='duration')
        return [r for r in self.all() if r.duration == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Coupon(id=record_id, **validate(data))

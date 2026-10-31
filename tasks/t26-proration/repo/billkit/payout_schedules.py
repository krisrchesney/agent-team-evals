"""Payout schedules: when collected money is paid out

Every record has an id like `pay_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATUS_VALUES = ('active', 'paused')


@dataclass
class PayoutSchedule:
    id: str
    name: str
    weekday: int = 0
    delay_days: int = 0
    status: str = 'active'


FIELDS = ('name', 'weekday', 'delay_days', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown payoutschedule field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['weekday'] = _int(data, 'weekday', 0, 6)
    out['delay_days'] = _int(data, 'delay_days', 0, 30)
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'active')
    return out


class PayoutScheduleRepo(Repository):
    prefix = 'pay'
    noun = 'payoutschedule'

    def create(self, **data):
        clean = validate(data)
        rec = PayoutSchedule(id=self.next_id(), **clean)
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

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return PayoutSchedule(id=record_id, **validate(data))

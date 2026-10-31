"""Subscriptions: who gets which alert

Every record has an id like `sub_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

CHANNEL_VALUES = ('email', 'sms', 'chat', 'webhook')


@dataclass
class Subscription:
    id: str
    alert: str
    target: str
    channel: str = 'email'
    active: bool = True


FIELDS = ('alert', 'target', 'channel', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown subscription field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['alert'] = _text(data, 'alert', required=True, limit=80)
    out['target'] = _text(data, 'target', required=True, limit=120)
    out['channel'] = _choice(data, 'channel', CHANNEL_VALUES, 'email')
    out['active'] = bool(data.get('active', True))
    return out


class SubscriptionRepo(Repository):
    prefix = 'sub'
    noun = 'subscription'

    def create(self, **data):
        clean = validate(data)
        rec = Subscription(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_alert(self, value):
        return [r for r in self.all() if r.alert == value]

    def find_by_target(self, value):
        return [r for r in self.all() if r.target == value]

    def with_channel(self, value):
        if value not in CHANNEL_VALUES:
            raise ValidationError(f"bad channel {value!r}", field='channel')
        return [r for r in self.all() if r.channel == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Subscription(id=record_id, **validate(data))

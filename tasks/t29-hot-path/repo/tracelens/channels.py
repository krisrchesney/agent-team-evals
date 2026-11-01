"""Channels: acquisition channels

Every record has an id like `chn_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

MEDIUM_VALUES = ('organic', 'paid', 'email', 'social', 'referral')


@dataclass
class Channel:
    id: str
    name: str
    medium: str = 'organic'
    pattern: str = ''


FIELDS = ('name', 'medium', 'pattern',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown channel field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['medium'] = _choice(data, 'medium', MEDIUM_VALUES, 'organic')
    out['pattern'] = _text(data, 'pattern', required=False, limit=120)
    return out


class ChannelRepo(Repository):
    prefix = 'chn'
    noun = 'channel'

    def create(self, **data):
        clean = validate(data)
        rec = Channel(id=self.next_id(), **clean)
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

    def find_by_pattern(self, value):
        return [r for r in self.all() if r.pattern == value]

    def with_medium(self, value):
        if value not in MEDIUM_VALUES:
            raise ValidationError(f"bad medium {value!r}", field='medium')
        return [r for r in self.all() if r.medium == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Channel(id=record_id, **validate(data))

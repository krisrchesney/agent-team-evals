"""Blocklist: ips and user ids that are ignored

Every record has an id like `blk_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

KIND_VALUES = ('ip', 'user')


@dataclass
class Blocked:
    id: str
    value: str
    kind: str = 'ip'
    reason: str = ''


FIELDS = ('value', 'kind', 'reason',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown blocked field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['value'] = _text(data, 'value', required=True, limit=80)
    out['kind'] = _choice(data, 'kind', KIND_VALUES, 'ip')
    out['reason'] = _text(data, 'reason', required=False, limit=200)
    return out


class BlockedRepo(Repository):
    prefix = 'blk'
    noun = 'blocked'

    def create(self, **data):
        clean = validate(data)
        rec = Blocked(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_value(self, value):
        return [r for r in self.all() if r.value == value]

    def find_by_reason(self, value):
        return [r for r in self.all() if r.reason == value]

    def with_kind(self, value):
        if value not in KIND_VALUES:
            raise ValidationError(f"bad kind {value!r}", field='kind')
        return [r for r in self.all() if r.kind == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Blocked(id=record_id, **validate(data))

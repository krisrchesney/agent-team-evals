"""Digests: scheduled summary emails

Every record has an id like `dig_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

CADENCE_VALUES = ('daily', 'weekly', 'monthly')


@dataclass
class Digest:
    id: str
    name: str
    recipient: str
    cadence: str = 'weekly'
    enabled: bool = True


FIELDS = ('name', 'recipient', 'cadence', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown digest field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['recipient'] = _email(data, 'recipient')
    out['cadence'] = _choice(data, 'cadence', CADENCE_VALUES, 'weekly')
    out['enabled'] = bool(data.get('enabled', True))
    return out


class DigestRepo(Repository):
    prefix = 'dig'
    noun = 'digest'

    def create(self, **data):
        clean = validate(data)
        rec = Digest(id=self.next_id(), **clean)
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

    def with_cadence(self, value):
        if value not in CADENCE_VALUES:
            raise ValidationError(f"bad cadence {value!r}", field='cadence')
        return [r for r in self.all() if r.cadence == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Digest(id=record_id, **validate(data))

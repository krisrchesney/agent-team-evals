"""Owners: teams responsible for jobs

Every record has an id like `own_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

TIER_VALUES = ('standard', 'critical')


@dataclass
class Owner:
    id: str
    name: str
    email: str
    pager: str = ''
    tier: str = 'standard'


FIELDS = ('name', 'email', 'pager', 'tier',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown owner field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['email'] = _email(data, 'email')
    out['pager'] = _text(data, 'pager', required=False, limit=40)
    out['tier'] = _choice(data, 'tier', TIER_VALUES, 'standard')
    return out


class OwnerRepo(Repository):
    prefix = 'own'
    noun = 'owner'

    def create(self, **data):
        clean = validate(data)
        rec = Owner(id=self.next_id(), **clean)
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

    def find_by_pager(self, value):
        return [r for r in self.all() if r.pager == value]

    def with_tier(self, value):
        if value not in TIER_VALUES:
            raise ValidationError(f"bad tier {value!r}", field='tier')
        return [r for r in self.all() if r.tier == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Owner(id=record_id, **validate(data))

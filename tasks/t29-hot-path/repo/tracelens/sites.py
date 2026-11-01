"""Sites: websites that send events

Every record has an id like `sit_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Site:
    id: str
    name: str
    domain: str
    timezone: str
    active: bool = True


FIELDS = ('name', 'domain', 'timezone', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown site field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['domain'] = _text(data, 'domain', required=True, limit=120)
    out['timezone'] = _text(data, 'timezone', required=True, limit=40)
    out['active'] = bool(data.get('active', True))
    return out


class SiteRepo(Repository):
    prefix = 'sit'
    noun = 'site'

    def create(self, **data):
        clean = validate(data)
        rec = Site(id=self.next_id(), **clean)
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

    def find_by_domain(self, value):
        return [r for r in self.all() if r.domain == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Site(id=record_id, **validate(data))

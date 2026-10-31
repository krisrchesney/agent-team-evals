"""Clusters: groups of peers

Every record has an id like `clu_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATE_VALUES = ('active', 'draining', 'retired')


@dataclass
class Cluster:
    id: str
    name: str
    region: str
    size: int = 1
    state: str = 'active'


FIELDS = ('name', 'region', 'size', 'state',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown cluster field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['region'] = _text(data, 'region', required=True, limit=30)
    out['size'] = _int(data, 'size', 1, 1000)
    out['state'] = _choice(data, 'state', STATE_VALUES, 'active')
    return out


class ClusterRepo(Repository):
    prefix = 'clu'
    noun = 'cluster'

    def create(self, **data):
        clean = validate(data)
        rec = Cluster(id=self.next_id(), **clean)
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

    def find_by_region(self, value):
        return [r for r in self.all() if r.region == value]

    def with_state(self, value):
        if value not in STATE_VALUES:
            raise ValidationError(f"bad state {value!r}", field='state')
        return [r for r in self.all() if r.state == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Cluster(id=record_id, **validate(data))

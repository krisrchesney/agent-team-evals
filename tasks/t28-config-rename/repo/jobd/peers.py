"""Peers: other jobd nodes in the cluster

Every record has an id like `pee_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATE_VALUES = ('joining', 'up', 'draining', 'down')


@dataclass
class Peer:
    id: str
    host: str
    port: int = 1
    zone: str = ''
    state: str = 'joining'


FIELDS = ('host', 'port', 'zone', 'state',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown peer field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['host'] = _text(data, 'host', required=True, limit=120)
    out['port'] = _int(data, 'port', 1, 65535)
    out['zone'] = _text(data, 'zone', required=False, limit=30)
    out['state'] = _choice(data, 'state', STATE_VALUES, 'joining')
    return out


class PeerRepo(Repository):
    prefix = 'pee'
    noun = 'peer'

    def create(self, **data):
        clean = validate(data)
        rec = Peer(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_host(self, value):
        return [r for r in self.all() if r.host == value]

    def find_by_zone(self, value):
        return [r for r in self.all() if r.zone == value]

    def with_state(self, value):
        if value not in STATE_VALUES:
            raise ValidationError(f"bad state {value!r}", field='state')
        return [r for r in self.all() if r.state == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Peer(id=record_id, **validate(data))

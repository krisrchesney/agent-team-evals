"""Deployments: versions of jobd rolled out

Every record has an id like `dep_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STRATEGY_VALUES = ('rolling', 'all_at_once', 'canary')


@dataclass
class Deployment:
    id: str
    version: str
    cluster: str
    strategy: str = 'rolling'
    done: bool = False


FIELDS = ('version', 'cluster', 'strategy', 'done',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown deployment field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['version'] = _text(data, 'version', required=True, limit=20)
    out['cluster'] = _text(data, 'cluster', required=True, limit=80)
    out['strategy'] = _choice(data, 'strategy', STRATEGY_VALUES, 'rolling')
    out['done'] = bool(data.get('done', False))
    return out


class DeploymentRepo(Repository):
    prefix = 'dep'
    noun = 'deployment'

    def create(self, **data):
        clean = validate(data)
        rec = Deployment(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_version(self, value):
        return [r for r in self.all() if r.version == value]

    def find_by_cluster(self, value):
        return [r for r in self.all() if r.cluster == value]

    def with_strategy(self, value):
        if value not in STRATEGY_VALUES:
            raise ValidationError(f"bad strategy {value!r}", field='strategy')
        return [r for r in self.all() if r.strategy == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Deployment(id=record_id, **validate(data))

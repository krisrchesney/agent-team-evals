"""Query rules: rewrites applied before searching

Every record has an id like `rul_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class QueryRule:
    id: str
    name: str
    pattern: str
    replacement: str
    active: bool = True


FIELDS = ('name', 'pattern', 'replacement', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown queryrule field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['pattern'] = _text(data, 'pattern', required=True, limit=120)
    out['replacement'] = _text(data, 'replacement', required=True, limit=120)
    out['active'] = bool(data.get('active', True))
    return out


class QueryRuleRepo(Repository):
    prefix = 'rul'
    noun = 'queryrule'

    def create(self, **data):
        clean = validate(data)
        rec = QueryRule(id=self.next_id(), **clean)
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


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return QueryRule(id=record_id, **validate(data))

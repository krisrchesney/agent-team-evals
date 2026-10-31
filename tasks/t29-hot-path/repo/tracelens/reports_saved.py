"""Reports saved: saved report runs

Every record has an id like `rpt_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

KIND_VALUES = ('pages', 'sessions', 'funnel')


@dataclass
class Report:
    id: str
    name: str
    kind: str = 'pages'
    params: str = ''
    rows: int = 0


FIELDS = ('name', 'kind', 'params', 'rows',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown report field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['kind'] = _choice(data, 'kind', KIND_VALUES, 'pages')
    out['params'] = _text(data, 'params', required=False, limit=300)
    out['rows'] = _int(data, 'rows', 0, 100000000)
    return out


class ReportRepo(Repository):
    prefix = 'rpt'
    noun = 'report'

    def create(self, **data):
        clean = validate(data)
        rec = Report(id=self.next_id(), **clean)
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

    def find_by_params(self, value):
        return [r for r in self.all() if r.params == value]

    def with_kind(self, value):
        if value not in KIND_VALUES:
            raise ValidationError(f"bad kind {value!r}", field='kind')
        return [r for r in self.all() if r.kind == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Report(id=record_id, **validate(data))

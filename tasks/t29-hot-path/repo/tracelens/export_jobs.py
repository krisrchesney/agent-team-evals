"""Export jobs: scheduled exports

Every record has an id like `exp_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

FORMAT_VALUES = ('csv', 'json')
STATUS_VALUES = ('queued', 'running', 'done', 'failed')


@dataclass
class ExportJob:
    id: str
    name: str
    destination: str
    format: str = 'csv'
    status: str = 'queued'


FIELDS = ('name', 'destination', 'format', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown exportjob field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['destination'] = _text(data, 'destination', required=True, limit=200)
    out['format'] = _choice(data, 'format', FORMAT_VALUES, 'csv')
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'queued')
    return out


class ExportJobRepo(Repository):
    prefix = 'exp'
    noun = 'exportjob'

    def create(self, **data):
        clean = validate(data)
        rec = ExportJob(id=self.next_id(), **clean)
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

    def find_by_destination(self, value):
        return [r for r in self.all() if r.destination == value]

    def with_format(self, value):
        if value not in FORMAT_VALUES:
            raise ValidationError(f"bad format {value!r}", field='format')
        return [r for r in self.all() if r.format == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return ExportJob(id=record_id, **validate(data))

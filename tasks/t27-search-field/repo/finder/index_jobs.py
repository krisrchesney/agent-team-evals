"""Index jobs: bulk indexing runs

Every record has an id like `job_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STATUS_VALUES = ('queued', 'running', 'done', 'failed')


@dataclass
class IndexJob:
    id: str
    collection: str
    source: str
    batch_size: int = 1
    status: str = 'queued'


FIELDS = ('collection', 'source', 'batch_size', 'status',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown indexjob field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['collection'] = _text(data, 'collection', required=True, limit=80)
    out['source'] = _text(data, 'source', required=True, limit=200)
    out['batch_size'] = _int(data, 'batch_size', 1, 5000)
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'queued')
    return out


class IndexJobRepo(Repository):
    prefix = 'job'
    noun = 'indexjob'

    def create(self, **data):
        clean = validate(data)
        rec = IndexJob(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_collection(self, value):
        return [r for r in self.all() if r.collection == value]

    def find_by_source(self, value):
        return [r for r in self.all() if r.source == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return IndexJob(id=record_id, **validate(data))

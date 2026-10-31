"""Runbooks: links from alerts to instructions

Every record has an id like `run_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Runbook:
    id: str
    alert: str
    title: str
    url: str
    reviewed: str = ''


FIELDS = ('alert', 'title', 'url', 'reviewed',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown runbook field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['alert'] = _text(data, 'alert', required=True, limit=80)
    out['title'] = _text(data, 'title', required=True, limit=120)
    out['url'] = _text(data, 'url', required=True, limit=300)
    out['reviewed'] = _text(data, 'reviewed', required=False, limit=20)
    return out


class RunbookRepo(Repository):
    prefix = 'run'
    noun = 'runbook'

    def create(self, **data):
        clean = validate(data)
        rec = Runbook(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_alert(self, value):
        return [r for r in self.all() if r.alert == value]

    def find_by_title(self, value):
        return [r for r in self.all() if r.title == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Runbook(id=record_id, **validate(data))

"""Incidents: operational incidents

Every record has an id like `inc_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

SEVERITY_VALUES = ('minor', 'major', 'critical')
STATUS_VALUES = ('open', 'mitigated', 'closed')


@dataclass
class Incident:
    id: str
    title: str
    severity: str = 'minor'
    status: str = 'open'
    commander: str = ''


FIELDS = ('title', 'severity', 'status', 'commander',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown incident field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['title'] = _text(data, 'title', required=True, limit=120)
    out['severity'] = _choice(data, 'severity', SEVERITY_VALUES, 'minor')
    out['status'] = _choice(data, 'status', STATUS_VALUES, 'open')
    out['commander'] = _text(data, 'commander', required=False, limit=60)
    return out


class IncidentRepo(Repository):
    prefix = 'inc'
    noun = 'incident'

    def create(self, **data):
        clean = validate(data)
        rec = Incident(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_title(self, value):
        return [r for r in self.all() if r.title == value]

    def find_by_commander(self, value):
        return [r for r in self.all() if r.commander == value]

    def with_severity(self, value):
        if value not in SEVERITY_VALUES:
            raise ValidationError(f"bad severity {value!r}", field='severity')
        return [r for r in self.all() if r.severity == value]

    def with_status(self, value):
        if value not in STATUS_VALUES:
            raise ValidationError(f"bad status {value!r}", field='status')
        return [r for r in self.all() if r.status == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Incident(id=record_id, **validate(data))

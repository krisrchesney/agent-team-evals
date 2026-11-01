"""Tickets: support tickets that mention billing

Every record has an id like `tkt_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

PRIORITY_VALUES = ('low', 'normal', 'high')


@dataclass
class Ticket:
    id: str
    customer: str
    subject: str
    body: str = ''
    priority: str = 'normal'


FIELDS = ('customer', 'subject', 'body', 'priority',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown ticket field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['subject'] = _text(data, 'subject', required=True, limit=120)
    out['body'] = _text(data, 'body', required=False, limit=2000)
    out['priority'] = _choice(data, 'priority', PRIORITY_VALUES, 'normal')
    return out


class TicketRepo(Repository):
    prefix = 'tkt'
    noun = 'ticket'

    def create(self, **data):
        clean = validate(data)
        rec = Ticket(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_customer(self, value):
        return [r for r in self.all() if r.customer == value]

    def find_by_subject(self, value):
        return [r for r in self.all() if r.subject == value]

    def with_priority(self, value):
        if value not in PRIORITY_VALUES:
            raise ValidationError(f"bad priority {value!r}", field='priority')
        return [r for r in self.all() if r.priority == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Ticket(id=record_id, **validate(data))

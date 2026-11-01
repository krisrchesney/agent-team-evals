"""Feedback: thumbs up or down on a result

Every record has an id like `fbk_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

VERDICT_VALUES = ('up', 'down')


@dataclass
class Feedback:
    id: str
    query: str
    doc: str
    verdict: str = 'up'
    comment: str = ''


FIELDS = ('query', 'doc', 'verdict', 'comment',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown feedback field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['query'] = _text(data, 'query', required=True, limit=200)
    out['doc'] = _text(data, 'doc', required=True, limit=64)
    out['verdict'] = _choice(data, 'verdict', VERDICT_VALUES, 'up')
    out['comment'] = _text(data, 'comment', required=False, limit=400)
    return out


class FeedbackRepo(Repository):
    prefix = 'fbk'
    noun = 'feedback'

    def create(self, **data):
        clean = validate(data)
        rec = Feedback(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_query(self, value):
        return [r for r in self.all() if r.query == value]

    def find_by_doc(self, value):
        return [r for r in self.all() if r.doc == value]

    def with_verdict(self, value):
        if value not in VERDICT_VALUES:
            raise ValidationError(f"bad verdict {value!r}", field='verdict')
        return [r for r in self.all() if r.verdict == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Feedback(id=record_id, **validate(data))

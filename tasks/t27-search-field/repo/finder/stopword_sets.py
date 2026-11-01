"""Stopword sets: extra stop words for a collection

Every record has an id like `stp_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

LANGUAGE_VALUES = ('en', 'de', 'fr', 'es')


@dataclass
class StopwordSet:
    id: str
    name: str
    words: str
    language: str = 'en'


FIELDS = ('name', 'words', 'language',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown stopwordset field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['words'] = _text(data, 'words', required=True, limit=600)
    out['language'] = _choice(data, 'language', LANGUAGE_VALUES, 'en')
    return out


class StopwordSetRepo(Repository):
    prefix = 'stp'
    noun = 'stopwordset'

    def create(self, **data):
        clean = validate(data)
        rec = StopwordSet(id=self.next_id(), **clean)
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

    def find_by_words(self, value):
        return [r for r in self.all() if r.words == value]

    def with_language(self, value):
        if value not in LANGUAGE_VALUES:
            raise ValidationError(f"bad language {value!r}", field='language')
        return [r for r in self.all() if r.language == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return StopwordSet(id=record_id, **validate(data))

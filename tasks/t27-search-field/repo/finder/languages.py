"""Languages: analysis settings per language

Every record has an id like `lng_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

STEMMER_VALUES = ('none', 'light', 'aggressive')


@dataclass
class Language:
    id: str
    code: str
    name: str
    stemmer: str = 'light'
    enabled: bool = True


FIELDS = ('code', 'name', 'stemmer', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown language field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['code'] = _text(data, 'code', required=True, limit=5)
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['stemmer'] = _choice(data, 'stemmer', STEMMER_VALUES, 'light')
    out['enabled'] = bool(data.get('enabled', True))
    return out


class LanguageRepo(Repository):
    prefix = 'lng'
    noun = 'language'

    def create(self, **data):
        clean = validate(data)
        rec = Language(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_code(self, value):
        return [r for r in self.all() if r.code == value]

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]

    def with_stemmer(self, value):
        if value not in STEMMER_VALUES:
            raise ValidationError(f"bad stemmer {value!r}", field='stemmer')
        return [r for r in self.all() if r.stemmer == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Language(id=record_id, **validate(data))

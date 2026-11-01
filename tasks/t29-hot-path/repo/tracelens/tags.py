"""Tags: labels for pages

Every record has an id like `tag_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

COLOR_VALUES = ('gray', 'red', 'green', 'blue')


@dataclass
class Tag:
    id: str
    name: str
    color: str = 'gray'
    note: str = ''


FIELDS = ('name', 'color', 'note',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown tag field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=40)
    out['color'] = _choice(data, 'color', COLOR_VALUES, 'gray')
    out['note'] = _text(data, 'note', required=False, limit=120)
    return out


class TagRepo(Repository):
    prefix = 'tag'
    noun = 'tag'

    def create(self, **data):
        clean = validate(data)
        rec = Tag(id=self.next_id(), **clean)
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

    def find_by_note(self, value):
        return [r for r in self.all() if r.note == value]

    def with_color(self, value):
        if value not in COLOR_VALUES:
            raise ValidationError(f"bad color {value!r}", field='color')
        return [r for r in self.all() if r.color == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Tag(id=record_id, **validate(data))

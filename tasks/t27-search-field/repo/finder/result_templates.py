"""Result templates: how a hit is rendered

Every record has an id like `tpl_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class ResultTemplate:
    id: str
    name: str
    title_format: str
    show_tags: bool = True
    snippet_width: int = 20


FIELDS = ('name', 'title_format', 'show_tags', 'snippet_width',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown resulttemplate field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['title_format'] = _text(data, 'title_format', required=True, limit=120)
    out['show_tags'] = bool(data.get('show_tags', True))
    out['snippet_width'] = _int(data, 'snippet_width', 20, 400)
    return out


class ResultTemplateRepo(Repository):
    prefix = 'tpl'
    noun = 'resulttemplate'

    def create(self, **data):
        clean = validate(data)
        rec = ResultTemplate(id=self.next_id(), **clean)
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

    def find_by_title_format(self, value):
        return [r for r in self.all() if r.title_format == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return ResultTemplate(id=record_id, **validate(data))

"""Pixels: tracking pixels

Every record has an id like `pix_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Pixel:
    id: str
    site: str
    label: str
    snippet_version: int = 1
    enabled: bool = True


FIELDS = ('site', 'label', 'snippet_version', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown pixel field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['site'] = _text(data, 'site', required=True, limit=80)
    out['label'] = _text(data, 'label', required=True, limit=60)
    out['snippet_version'] = _int(data, 'snippet_version', 1, 100)
    out['enabled'] = bool(data.get('enabled', True))
    return out


class PixelRepo(Repository):
    prefix = 'pix'
    noun = 'pixel'

    def create(self, **data):
        clean = validate(data)
        rec = Pixel(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_site(self, value):
        return [r for r in self.all() if r.site == value]

    def find_by_label(self, value):
        return [r for r in self.all() if r.label == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Pixel(id=record_id, **validate(data))

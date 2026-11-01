"""Products: things that can appear on an invoice line

Every record has an id like `prd_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Product:
    id: str
    sku: str
    name: str
    description: str = ''
    active: bool = True


FIELDS = ('sku', 'name', 'description', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown product field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['sku'] = _text(data, 'sku', required=True, limit=32)
    out['name'] = _text(data, 'name', required=True, limit=80)
    out['description'] = _text(data, 'description', required=False, limit=300)
    out['active'] = bool(data.get('active', True))
    return out


class ProductRepo(Repository):
    prefix = 'prd'
    noun = 'product'

    def create(self, **data):
        clean = validate(data)
        rec = Product(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_sku(self, value):
        return [r for r in self.all() if r.sku == value]

    def find_by_name(self, value):
        return [r for r in self.all() if r.name == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Product(id=record_id, **validate(data))

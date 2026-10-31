"""Invoice templates: layouts used when an invoice is rendered

Every record has an id like `tpl_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

LOCALE_VALUES = ('en', 'de', 'fr', 'es')


@dataclass
class InvoiceTemplate:
    id: str
    name: str
    footer: str = ''
    locale: str = 'en'
    show_tax_id: bool = True


FIELDS = ('name', 'footer', 'locale', 'show_tax_id',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown invoicetemplate field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['footer'] = _text(data, 'footer', required=False, limit=300)
    out['locale'] = _choice(data, 'locale', LOCALE_VALUES, 'en')
    out['show_tax_id'] = bool(data.get('show_tax_id', True))
    return out


class InvoiceTemplateRepo(Repository):
    prefix = 'tpl'
    noun = 'invoicetemplate'

    def create(self, **data):
        clean = validate(data)
        rec = InvoiceTemplate(id=self.next_id(), **clean)
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

    def find_by_footer(self, value):
        return [r for r in self.all() if r.footer == value]

    def with_locale(self, value):
        if value not in LOCALE_VALUES:
            raise ValidationError(f"bad locale {value!r}", field='locale')
        return [r for r in self.all() if r.locale == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return InvoiceTemplate(id=record_id, **validate(data))

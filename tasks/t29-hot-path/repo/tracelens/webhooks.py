"""Webhooks: urls called when alerts fire

Every record has an id like `whk_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Webhook:
    id: str
    url: str
    secret: str = ''
    alert: str = ''
    enabled: bool = True


FIELDS = ('url', 'secret', 'alert', 'enabled',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown webhook field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['url'] = _text(data, 'url', required=True, limit=200)
    out['secret'] = _text(data, 'secret', required=False, limit=64)
    out['alert'] = _text(data, 'alert', required=False, limit=64)
    out['enabled'] = bool(data.get('enabled', True))
    return out


class WebhookRepo(Repository):
    prefix = 'whk'
    noun = 'webhook'

    def create(self, **data):
        clean = validate(data)
        rec = Webhook(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_url(self, value):
        return [r for r in self.all() if r.url == value]

    def find_by_secret(self, value):
        return [r for r in self.all() if r.secret == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Webhook(id=record_id, **validate(data))

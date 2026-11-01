"""Embeds: public share links

Every record has an id like `emb_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class Embed:
    id: str
    dashboard: str
    token: str
    expires: str = ''
    revoked: bool = False


FIELDS = ('dashboard', 'token', 'expires', 'revoked',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown embed field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['dashboard'] = _text(data, 'dashboard', required=True, limit=80)
    out['token'] = _text(data, 'token', required=True, limit=32)
    out['expires'] = _text(data, 'expires', required=False, limit=20)
    out['revoked'] = bool(data.get('revoked', False))
    return out


class EmbedRepo(Repository):
    prefix = 'emb'
    noun = 'embed'

    def create(self, **data):
        clean = validate(data)
        rec = Embed(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_dashboard(self, value):
        return [r for r in self.all() if r.dashboard == value]

    def find_by_token(self, value):
        return [r for r in self.all() if r.token == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Embed(id=record_id, **validate(data))

"""Members: people with access

Every record has an id like `mem_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text

ROLE_VALUES = ('viewer', 'analyst', 'admin')


@dataclass
class Member:
    id: str
    name: str
    email: str
    role: str = 'viewer'
    active: bool = True


FIELDS = ('name', 'email', 'role', 'active',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown member field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['name'] = _text(data, 'name', required=True, limit=60)
    out['email'] = _email(data, 'email')
    out['role'] = _choice(data, 'role', ROLE_VALUES, 'viewer')
    out['active'] = bool(data.get('active', True))
    return out


class MemberRepo(Repository):
    prefix = 'mem'
    noun = 'member'

    def create(self, **data):
        clean = validate(data)
        rec = Member(id=self.next_id(), **clean)
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

    def with_role(self, value):
        if value not in ROLE_VALUES:
            raise ValidationError(f"bad role {value!r}", field='role')
        return [r for r in self.all() if r.role == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return Member(id=record_id, **validate(data))

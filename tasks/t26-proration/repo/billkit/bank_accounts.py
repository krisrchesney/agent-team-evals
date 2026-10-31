"""Bank accounts: accounts we pay refunds into

Every record has an id like `bnk_0001` handed out by the repository."""
from dataclasses import asdict, dataclass

from .errors import NotFound, ValidationError
from .repo_base import Repository
from .validators import choice as _choice, email as _email, integer as _int, text as _text



@dataclass
class BankAccount:
    id: str
    customer: str
    holder: str
    iban_hint: str
    verified: bool = False


FIELDS = ('customer', 'holder', 'iban_hint', 'verified',)


def validate(data):
    """Return the cleaned fields, or raise ValidationError for the first bad one."""
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValidationError(f"unknown bankaccount field {unknown[0]!r}", field=unknown[0])
    out = {}
    out['customer'] = _text(data, 'customer', required=True, limit=80)
    out['holder'] = _text(data, 'holder', required=True, limit=80)
    out['iban_hint'] = _text(data, 'iban_hint', required=True, limit=8)
    out['verified'] = bool(data.get('verified', False))
    return out


class BankAccountRepo(Repository):
    prefix = 'bnk'
    noun = 'bankaccount'

    def create(self, **data):
        clean = validate(data)
        rec = BankAccount(id=self.next_id(), **clean)
        return self.save(rec)

    def update(self, record_id, **changes):
        rec = self.get(record_id)
        merged = {**to_dict(rec), **changes}
        merged.pop('id')
        clean = validate(merged)
        for key, value in clean.items():
            setattr(rec, key, value)
        return rec

    def find_by_customer(self, value):
        return [r for r in self.all() if r.customer == value]

    def find_by_holder(self, value):
        return [r for r in self.all() if r.holder == value]


def to_dict(rec):
    return asdict(rec)


def from_dict(data):
    data = dict(data)
    record_id = data.pop('id')
    return BankAccount(id=record_id, **validate(data))

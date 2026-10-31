"""A tenant is everything one customer owns. Module functions receive it where they used to receive the service."""
import re

from . import validate
from .audit import Audit
from .errors import Conflict, InvalidInput, UnknownTenant
from .ids import Ids
from .outbox import Outbox
from .store import Store

TENANT_ID = re.compile(r"^[a-z0-9-]{2,20}$")


class Tenant:
    def __init__(self, tenant, name, clock, subscribers):
        self.tenant = tenant
        self.name = name
        self.clock = clock
        self.store = Store()
        self.ids = Ids()
        self.outbox = Outbox(clock, tenant, subscribers)
        self.audit = Audit(clock)


class Registry:
    def __init__(self, clock, subscribers):
        self.clock = clock
        self.subscribers = subscribers
        self._tenants = {}

    def create(self, tenant_id, name):
        if not isinstance(tenant_id, str) or not TENANT_ID.match(tenant_id):
            raise InvalidInput("a tenant id is 2 to 20 lower-case letters, digits or dashes", param="tenant")
        name = validate.text(name, "name", max_len=60)
        if tenant_id in self._tenants:
            raise Conflict(f"tenant {tenant_id} already exists", param="tenant")
        self._tenants[tenant_id] = Tenant(tenant_id, name, self.clock, self.subscribers)
        return self._tenants[tenant_id]

    def get(self, tenant_id):
        found = self._tenants.get(tenant_id) if isinstance(tenant_id, str) else None
        if found is None:
            raise UnknownTenant(f"no tenant {tenant_id!r}", param="tenant")
        return found

    def drop(self, tenant_id):
        return self._tenants.pop(tenant_id)

    def all(self):
        return [self._tenants[k] for k in sorted(self._tenants)]

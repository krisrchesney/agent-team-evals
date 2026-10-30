"""The caller of an operation: who they are, what they may do, and their idempotency key."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Context:
    actor: str
    scopes: frozenset = frozenset()
    idempotency_key: str | None = None

    def with_key(self, key):
        """The same caller with a different idempotency key (None for no key)."""
        return replace(self, idempotency_key=key)

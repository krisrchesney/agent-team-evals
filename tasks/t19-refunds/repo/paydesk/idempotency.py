"""Idempotency keys: a retried request with the same key returns the first result."""
import copy

from .errors import Conflict


class IdempotencyStore:
    def __init__(self):
        self._results = {}

    def run(self, ctx, name, params, body):
        """Run body() at most once per (actor, key). Without a key, just run it.

        A replay returns a copy of the first result. Reusing a key for another operation or other
        params raises Conflict. Failures are not stored, so a failed request can be retried.
        """
        key = ctx.idempotency_key
        if key is None:
            return body()
        slot = (ctx.actor, key)
        if slot in self._results:
            first_name, first_params, result = self._results[slot]
            if (first_name, first_params) != (name, params):
                raise Conflict(f"idempotency key {key!r} was used for a different request",
                               code="idempotency_mismatch")
            return copy.deepcopy(result)
        result = body()
        self._results[slot] = (name, dict(params), copy.deepcopy(result))
        return result

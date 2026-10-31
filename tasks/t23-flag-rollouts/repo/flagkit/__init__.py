"""flagkit: feature flags with stable percentage rollouts.

    from flagkit import Context, FlagClient
    client = FlagClient()
    client.add({"key": "new-checkout", "type": "rollout", "percent": 25})
    client.is_on("new-checkout", Context(user_id="u-17"))
"""
from .client import FlagClient
from .context import Context
from .decision import Decision
from .errors import FlagConfigError, FlagError, UnknownFlag
from .flag import Flag

__all__ = ["FlagClient", "Context", "Decision", "Flag", "FlagError", "FlagConfigError", "UnknownFlag"]

"""A sliding-window rate limit: each tenant may make at most RATE_LIMIT calls in any WINDOW_SECONDS."""
from datetime import timedelta

from .errors import RateLimited

RATE_LIMIT = 100
WINDOW_SECONDS = 60

_HITS = {}        # tenant -> [time of each recent call]


def hit(tenant, now):
    """Count one call by `tenant` at `now`, or raise RateLimited if its window is already full."""
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)
    recent = [t for t in _HITS.get(tenant, ()) if t > cutoff]
    if len(recent) >= RATE_LIMIT:
        _HITS[tenant] = recent
        raise RateLimited(f"at most {RATE_LIMIT} calls per {WINDOW_SECONDS} seconds")
    recent.append(now)
    _HITS[tenant] = recent


def drop_tenant(tenant):
    _HITS.pop(tenant, None)


def reset():
    _HITS.clear()

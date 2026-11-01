"""A sliding-window rate limit: at most RATE_LIMIT calls in any WINDOW_SECONDS, for the whole process."""
from datetime import timedelta

from .errors import RateLimited

RATE_LIMIT = 100
WINDOW_SECONDS = 60

_HITS = []


def hit(now):
    """Count one call at `now`, or raise RateLimited if the window is already full."""
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)
    _HITS[:] = [t for t in _HITS if t > cutoff]
    if len(_HITS) >= RATE_LIMIT:
        raise RateLimited(f"at most {RATE_LIMIT} calls per {WINDOW_SECONDS} seconds")
    _HITS.append(now)


def reset():
    _HITS.clear()

"""Counts per time bucket."""
from collections import Counter

HOUR_MS = 3600 * 1000
DAY_MS = 24 * HOUR_MS


def bucket(ts, size_ms):
    return ts - ts % size_ms


def counts_by_bucket(events, size_ms=HOUR_MS, kind=None):
    """bucket start -> number of events (of `kind`, if given), in time order."""
    counts = Counter(bucket(e.ts, size_ms) for e in events if kind is None or e.kind == kind)
    return dict(sorted(counts.items()))


def unique_users_by_bucket(events, size_ms=DAY_MS):
    seen = {}
    for e in events:
        seen.setdefault(bucket(e.ts, size_ms), set()).add(e.user)
    return {start: len(users) for start, users in sorted(seen.items())}


def busiest_bucket(events, size_ms=HOUR_MS):
    counts = counts_by_bucket(events, size_ms)
    if not counts:
        return None
    best = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
    return best


def moving_average(series, window=3):
    """Simple trailing average over a list of numbers."""
    out = []
    for i in range(len(series)):
        chunk = series[max(0, i - window + 1): i + 1]
        out.append(sum(chunk) / len(chunk))
    return out

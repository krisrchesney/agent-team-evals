"""Dropping repeated deliveries of the same event."""
from ..events import sort_key


def dedupe(events):
    """Keep one event per id.

    Shards deliver at least once and in any order, so the same id can show up several times. The
    earliest copy by (ts, shard, seq) is kept and the result is sorted by that key. The input list is
    not changed.
    """
    ordered = sorted(events, key=sort_key)
    seen = set()
    kept = []
    for event in ordered:
        if event.id in seen:
            continue
        seen.add(event.id)
        kept.append(event)
    return kept


def duplicate_count(events):
    return len(events) - len(dedupe(events))


def duplicate_ids(events):
    """Ids that were delivered more than once, sorted."""
    counts = {}
    for event in events:
        counts[event.id] = counts.get(event.id, 0) + 1
    return sorted(i for i, n in counts.items() if n > 1)

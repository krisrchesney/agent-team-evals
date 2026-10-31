"""Traffic by hour of day, for the "when are people here?" chart."""
from datetime import datetime, timezone


def hour_of_day(ts_ms):
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).hour


def views_by_hour(events):
    """A list of 24 counts, index = hour of day (UTC), views only."""
    counts = [0] * 24
    for event in events:
        if event.kind == "view":
            counts[hour_of_day(event.ts)] += 1
    return counts


def peak_hours(events, n=3):
    """The `n` busiest hours as (hour, views); ties go to the earlier hour."""
    counts = views_by_hour(events)
    ranked = sorted(range(24), key=lambda h: (-counts[h], h))
    return [(h, counts[h]) for h in ranked[:n]]


def quiet_hours(events, threshold=0.5):
    """Hours with fewer views than `threshold` times the hourly average."""
    counts = views_by_hour(events)
    average = sum(counts) / 24
    return [h for h, c in enumerate(counts) if c < threshold * average]


def share_in_hours(events, hours):
    """Share of views that happened in the given set of hours."""
    counts = views_by_hour(events)
    total = sum(counts)
    return sum(counts[h] for h in hours) / total if total else 0.0

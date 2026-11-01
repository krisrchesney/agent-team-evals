"""Retention: of the users first seen in a week, how many came back later?"""
from ..events import sort_key

WEEK_MS = 7 * 24 * 60 * 60 * 1000


def first_seen(events):
    """user -> timestamp of their earliest event."""
    first = {}
    for event in sorted(events, key=sort_key):
        first.setdefault(event.user, event.ts)
    return first


def weekly_cohorts(events, origin):
    """cohort week number (0 = week starting at `origin`) -> sorted list of users first seen then."""
    cohorts = {}
    for user, ts in first_seen(events).items():
        if ts < origin:
            continue
        cohorts.setdefault((ts - origin) // WEEK_MS, []).append(user)
    return {week: sorted(users) for week, users in sorted(cohorts.items())}


def retention_table(events, origin, weeks=4):
    """cohort week -> [share of the cohort active in week +0, +1, ... +weeks-1]."""
    cohorts = weekly_cohorts(events, origin)
    active = {}
    for event in events:
        active.setdefault(event.user, set()).add((event.ts - origin) // WEEK_MS)
    table = {}
    for week, users in cohorts.items():
        row = []
        for offset in range(weeks):
            hit = sum(1 for u in users if week + offset in active[u])
            row.append(hit / len(users))
        table[week] = row
    return table

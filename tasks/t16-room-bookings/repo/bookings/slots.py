"""Finding free time in a room."""
from datetime import datetime, time, timedelta

from . import rules

STEP = timedelta(minutes=15)
OPENS, CLOSES = time(8), time(18)


def free_starts(store, room_id, day, minutes):
    """Start times (datetimes) on `day` where a booking of `minutes` minutes would fit.

    Candidates are on the 15-minute grid inside opening hours; weekends have none. A candidate is
    free when no active booking of the room overlaps it. Lead time and budget are not considered.
    """
    if day.weekday() > 4:
        return []
    length = timedelta(minutes=minutes)
    cursor = datetime.combine(day, OPENS)
    last_end = datetime.combine(day, CLOSES)
    found = []
    while cursor + length <= last_end:
        if rules.find_conflict(store, room_id, cursor, cursor + length) is None:
            found.append(cursor)
        cursor += STEP
    return found


def next_free_start(store, room_id, day, minutes, not_before=None):
    """The earliest free start on `day`, at or after `not_before` if given, else None."""
    for start in free_starts(store, room_id, day, minutes):
        if not_before is None or start >= not_before:
            return start
    return None

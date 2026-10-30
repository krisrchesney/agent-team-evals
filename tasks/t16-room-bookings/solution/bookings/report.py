"""Plain-text reports."""
from decimal import ROUND_HALF_UP, Decimal

from .calendar_util import weekdays_between
from .fmt import money

DAY_MINUTES = 600  # 08:00 to 18:00


def _one_decimal(value):
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def utilization(store, first_day, last_day):
    """One line per room, sorted by name: share of the available weekday minutes that is booked."""
    available = weekdays_between(first_day, last_day) * DAY_MINUTES
    lines = []
    for room in sorted(store.rooms.values(), key=lambda r: r.name.lower()):
        booked = sum(int((b.end - b.start).total_seconds() // 60)
                     for b in store.active_for_room(room.id)
                     if first_day <= b.start.date() <= last_day)
        pct = _one_decimal(Decimal(booked) * 100 / available) if available else Decimal("0.0")
        hours = _one_decimal(Decimal(booked) / 60)
        lines.append(f"{room.name:<16}{pct:>6}%  {hours}h")
    return "\n".join(lines)


def agenda(store, day):
    """Everything booked on `day` (a date), earliest first, one line each:
    `09:00-10:30 Boardroom (Ann, 4 people)`. Says `Nothing booked` for an empty day."""
    entries = []
    for room in store.rooms.values():
        entries += [(b, room) for b in store.active_for_room(room.id) if b.start.date() == day]
    entries.sort(key=lambda e: (e[0].start, e[1].name.lower(), e[0].id))
    if not entries:
        return "Nothing booked"
    return "\n".join(
        f"{b.start:%H:%M}-{b.end:%H:%M} {room.name} ({store.user(b.user_id).name}, {b.attendees} people)"
        for b, room in entries)


def spend_report(store):
    """One line per team, sorted by name; teams that kept cancellation fees say so."""
    lines = []
    for t in sorted(store.teams.values(), key=lambda t: t.name):
        line = f"{t.name}: {money(t.spent_cents)} spent, {money(t.budget_cents)} left"
        if t.fees_cents:
            line += f", {money(t.fees_cents)} in fees"
        lines.append(line)
    return "\n".join(lines)


def waitlist_report(store):
    """`Boardroom: 2 waiting` per room that has waiting requests, sorted by room name."""
    counts = {}
    for entry in store.waitlist.values():
        counts[entry.room_id] = counts.get(entry.room_id, 0) + 1
    if not counts:
        return "Waitlist is empty"
    rooms = sorted(counts, key=lambda rid: store.room(rid).name.lower())
    return "\n".join(f"{store.room(rid).name}: {counts[rid]} waiting" for rid in rooms)

"""Booking rules that depend only on the request, the clock and what is already booked."""
from datetime import time, timedelta

from .errors import Conflict, InvalidRequest

MIN_MINUTES, MAX_MINUTES = 30, 240
LEAD_TIME = timedelta(minutes=15)


def check_window(start, end):
    """Time-slot rules, checked in this order; the first broken one is reported."""
    if end <= start:
        raise InvalidRequest("end must be after start")
    for t in (start, end):
        if t.minute % 15 or t.second or t.microsecond:
            raise InvalidRequest("times must be on 15-minute marks")
    minutes = int((end - start).total_seconds() // 60)
    if not MIN_MINUTES <= minutes <= MAX_MINUTES:
        raise InvalidRequest(f"booking must last {MIN_MINUTES} to {MAX_MINUTES} minutes")
    if start.date() != end.date() or start.weekday() > 4 or start.time() < time(8) or end.time() > time(18):
        raise InvalidRequest("bookings must be on weekdays between 08:00 and 18:00")


def check_attendees(room, attendees):
    if not 1 <= attendees <= room.capacity:
        raise InvalidRequest(f"attendees must be between 1 and {room.capacity}")


def check_lead_time(now, start):
    if start - now < LEAD_TIME:
        raise InvalidRequest("bookings must start at least 15 minutes from now")


def find_conflict(store, room_id, start, end):
    """The earliest active booking of the room that overlaps [start, end), or None."""
    for booking in store.active_for_room(room_id):
        if booking.start < end and start < booking.end:
            return booking
    return None


def check_free(store, room_id, start, end):
    clash = find_conflict(store, room_id, start, end)
    if clash:
        raise Conflict(f"room is already booked from {clash.start:%H:%M} to {clash.end:%H:%M}")

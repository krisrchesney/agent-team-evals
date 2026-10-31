"""iCalendar export. Every time is written in UTC with a trailing Z."""
from datetime import datetime

from .timeparse import UTC, localize
from .users import WEEKDAYS


def fmt_ics(dt):
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _local_instant(day, event, zone):
    """The instant of the event's local time of day on a local date."""
    return localize(datetime.combine(day, event.start.astimezone(zone).time()), zone)


def _rrule(event, zone):
    rule = event.rule
    parts = [f"FREQ={rule.freq.upper()}", f"INTERVAL={rule.interval}"]
    if rule.weekdays:
        parts.append("BYDAY=" + ",".join(WEEKDAYS[d][:2].upper() for d in rule.weekdays))
    if rule.count:
        parts.append(f"COUNT={rule.count}")
    if rule.until:
        parts.append("UNTIL=" + fmt_ics(_local_instant(rule.until, event, zone)))
    return "RRULE:" + ";".join(parts)


def export(calendar, events, now):
    """The active events of one calendar as an iCalendar document (CRLF line ends)."""
    zone = calendar.zone
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//sched//EN", f"X-WR-CALNAME:{calendar.name}"]
    for event in events:
        lines += ["BEGIN:VEVENT", f"UID:{event.id}@sched", f"DTSTAMP:{fmt_ics(now)}",
                  f"DTSTART:{fmt_ics(event.start)}", f"DTEND:{fmt_ics(event.start + event.duration)}",
                  f"SUMMARY:{event.title}"]
        if event.rule:
            lines.append(_rrule(event, zone))
        for day in sorted(event.skips):
            lines.append("EXDATE:" + fmt_ics(_local_instant(day, event, zone)))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

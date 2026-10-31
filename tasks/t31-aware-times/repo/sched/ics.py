"""iCalendar export. Times are floating (no zone), like the rest of sched."""
from datetime import datetime

from .users import WEEKDAYS


def fmt_ics(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def _rrule(event):
    rule = event.rule
    parts = [f"FREQ={rule.freq.upper()}", f"INTERVAL={rule.interval}"]
    if rule.weekdays:
        parts.append("BYDAY=" + ",".join(WEEKDAYS[d][:2].upper() for d in rule.weekdays))
    if rule.count:
        parts.append(f"COUNT={rule.count}")
    if rule.until:
        parts.append("UNTIL=" + fmt_ics(datetime.combine(rule.until, event.start.time())))
    return "RRULE:" + ";".join(parts)


def export(calendar, events, now):
    """The active events of one calendar as an iCalendar document (CRLF line ends)."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//sched//EN", f"X-WR-CALNAME:{calendar.name}"]
    for event in events:
        lines += ["BEGIN:VEVENT", f"UID:{event.id}@sched", f"DTSTAMP:{fmt_ics(now)}",
                  f"DTSTART:{fmt_ics(event.start)}", f"DTEND:{fmt_ics(event.start + event.duration)}",
                  f"SUMMARY:{event.title}"]
        if event.rule:
            lines.append(_rrule(event))
        for day in sorted(event.skips):
            lines.append("EXDATE:" + fmt_ics(datetime.combine(day, event.start.time())))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

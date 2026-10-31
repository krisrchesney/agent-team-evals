"""A small five-field cron expression matcher: minute hour day-of-month month day-of-week."""
from datetime import datetime

from .errors import ValidationError

_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
_NAMES = ["minute", "hour", "day of month", "month", "day of week"]


def _parse_field(text, low, high, name):
    allowed = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            if not step_text.isdigit() or int(step_text) < 1:
                raise ValidationError(f"bad step in {name}: {step_text!r}", field="cron")
            step = int(step_text)
        if part == "*":
            start, end = low, high
        elif "-" in part:
            a, b = part.split("-", 1)
            start, end = _number(a, low, high, name), _number(b, low, high, name)
        else:
            start = _number(part, low, high, name)
            end = high if step > 1 else start
        if start > end:
            raise ValidationError(f"backwards range in {name}", field="cron")
        allowed.update(range(start, end + 1, step))
    return allowed


def _number(text, low, high, name):
    if not text.isdigit() or not low <= int(text) <= high:
        raise ValidationError(f"{name} must be {low} to {high}, not {text!r}", field="cron")
    return int(text)


class Cron:
    def __init__(self, expression):
        parts = expression.split()
        if len(parts) != 5:
            raise ValidationError("a cron expression has five fields", field="cron")
        self.expression = expression
        self.fields = [
            _parse_field(text, low, high, name)
            for text, (low, high), name in zip(parts, _RANGES, _NAMES)
        ]

    def matches(self, when):
        minute, hour, dom, month, dow = self.fields
        return (
            when.minute in minute and when.hour in hour and when.day in dom
            and when.month in month and (when.isoweekday() % 7) in dow
        )

    def next_after(self, when, limit_days=366):
        """The first matching minute strictly after `when`, or None within `limit_days`."""
        probe = when.replace(second=0, microsecond=0)
        for _ in range(limit_days * 24 * 60):
            probe = probe.fromtimestamp(probe.timestamp() + 60)
            if self.matches(probe):
                return probe
        return None


def parse(expression):
    return Cron(expression)


def due(expressions, when: datetime):
    return [e for e in expressions if parse(e).matches(when)]

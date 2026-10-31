"""Parsing raw log lines into events.

A line looks like:  2026-03-01T10:15:30.250Z shard=2 seq=1841 id=ab12 user=u7 kind=view page=/pricing
"""
import re
from datetime import datetime, timezone

from ..errors import ValidationError
from ..events import Event

_PAIR = re.compile(r"(\w+)=(\S*)")
REQUIRED = ("id", "user", "kind", "page")


def parse_timestamp(text):
    """Milliseconds since the epoch for an ISO-8601 UTC timestamp ending in Z."""
    try:
        dt = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        try:
            dt = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValidationError(f"bad timestamp {text!r}", field="ts") from None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def parse_line(line):
    parts = line.strip().split(None, 1)
    if len(parts) != 2:
        raise ValidationError("a log line needs a timestamp and fields", field="line")
    ts = parse_timestamp(parts[0])
    fields = dict(_PAIR.findall(parts[1]))
    for name in REQUIRED:
        if not fields.get(name):
            raise ValidationError(f"missing {name}", field=name)
    try:
        shard, seq = int(fields.pop("shard", 0)), int(fields.pop("seq", 0))
    except ValueError:
        raise ValidationError("shard and seq must be whole numbers", field="shard") from None
    return Event(fields.pop("id"), fields.pop("user"), ts, fields.pop("kind"), fields.pop("page"),
                 shard, seq, fields)


def parse_lines(lines):
    """Parse many lines; returns (events, errors) where errors is [(line number, message)]."""
    events, errors = [], []
    for number, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            events.append(parse_line(line))
        except ValidationError as exc:
            errors.append((number, exc.message))
    return events, errors

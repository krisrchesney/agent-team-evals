"""Small time helpers; timestamps are integer milliseconds in UTC."""
from datetime import datetime, timezone


def to_iso(ts_ms):
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def day_of(ts_ms):
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def minutes(n):
    return n * 60 * 1000


def hours(n):
    return n * 60 * minutes(1)


def humanize(ms):
    """3_723_000 -> '1h 2m 3s'."""
    seconds = ms // 1000
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    parts = [f"{h}h"] if h else []
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

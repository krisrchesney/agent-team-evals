"""The event record every stage works on."""
from dataclasses import dataclass, field


@dataclass
class Event:
    id: str       # unique per event; the same id delivered twice is a duplicate
    user: str
    ts: int       # milliseconds since the epoch
    kind: str     # "view", "click", "ping", ...
    page: str
    shard: int = 0
    seq: int = 0  # position in the shard's own stream
    props: dict = field(default_factory=dict)


def sort_key(event):
    """The one order events are processed in: time, then shard, then position within the shard."""
    return (event.ts, event.shard, event.seq)


def make(event_id, user, ts, kind="view", page="/", shard=0, seq=0, **props):
    return Event(event_id, user, ts, kind, page, shard, seq, props)

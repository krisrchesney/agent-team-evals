"""Grouping a user's events into sessions."""
from dataclasses import dataclass, field

from ..events import sort_key

DEFAULT_GAP_MS = 30 * 60 * 1000
IGNORED_KINDS = frozenset({"ping"})


@dataclass
class Session:
    id: str
    user: str
    start: int
    end: int
    events: int = 1
    pages: list = field(default_factory=list)

    @property
    def duration_ms(self):
        return self.end - self.start


def sessionize(events, gap_ms=DEFAULT_GAP_MS):
    """Split every user's events into sessions.

    Events are taken in `sort_key` order, whatever order they are passed in; heartbeat ("ping")
    events do not count. A user's event continues their latest session unless more than `gap_ms`
    passed since that session's last event (exactly `gap_ms` still continues it); otherwise it starts a
    new one. Sessions are numbered s_000001, s_000002, ... in the order they were started, and returned
    in that order. `pages` lists each page once, in the order first visited.
    """
    ordered = sorted((e for e in events if e.kind not in IGNORED_KINDS), key=sort_key)
    sessions = []
    latest = {}  # user -> that user's latest session
    seen_pages = {}  # session id -> pages already listed
    for event in ordered:
        current = latest.get(event.user)
        if current is not None and event.ts - current.end <= gap_ms:
            current.end = event.ts
            current.events += 1
            pages = seen_pages[current.id]
            if event.page not in pages:
                pages.add(event.page)
                current.pages.append(event.page)
        else:
            current = Session(f"s_{len(sessions) + 1:06d}", event.user, event.ts, event.ts, 1, [event.page])
            sessions.append(current)
            latest[event.user] = current
            seen_pages[current.id] = {event.page}
    return sessions


def by_user(sessions):
    out = {}
    for session in sessions:
        out.setdefault(session.user, []).append(session)
    return out


def average_duration_ms(sessions):
    if not sessions:
        return 0.0
    return sum(s.duration_ms for s in sessions) / len(sessions)


def bounce_rate(sessions):
    """Share of sessions with a single event."""
    if not sessions:
        return 0.0
    return sum(1 for s in sessions if s.events == 1) / len(sessions)

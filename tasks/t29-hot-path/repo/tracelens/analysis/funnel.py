"""Funnels: how far do users get through an ordered list of pages?"""
from ..events import sort_key


def funnel(events, steps):
    """How many users reached each step, as a list the length of `steps`.

    A user is at step k once they viewed steps[0], then steps[1] later, and so on up to steps[k]
    (events in `sort_key` order; other kinds of event are ignored). Viewing a page again does not
    count twice, and viewing the steps out of order does not skip ahead.
    """
    users = sorted({e.user for e in events})
    reached = [0] * len(steps)
    for user in users:
        own = sorted([e for e in events if e.user == user and e.kind == "view"], key=sort_key)
        step = 0
        for event in own:
            if step < len(steps) and event.page == steps[step]:
                step += 1
        for i in range(step):
            reached[i] += 1
    return reached


def conversion(reached):
    """Share of the first step that reached the last (0.0 if nobody entered)."""
    if not reached or reached[0] == 0:
        return 0.0
    return reached[-1] / reached[0]


def drop_off(reached):
    """Users lost between consecutive steps."""
    return [reached[i] - reached[i + 1] for i in range(len(reached) - 1)]

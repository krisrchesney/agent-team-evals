"""Removing traffic from known bots before analysis."""
from .useragent import classify


def is_bot_event(event):
    agent = event.props.get("ua", "")
    return classify(agent)[2]


def drop_bots(events):
    """Events not marked as bot traffic. Events without a user agent are kept."""
    return [e for e in events if not is_bot_event(e)]


def bot_share(events):
    if not events:
        return 0.0
    return sum(1 for e in events if is_bot_event(e)) / len(events)


def split(events):
    humans, bots = [], []
    for e in events:
        (bots if is_bot_event(e) else humans).append(e)
    return humans, bots

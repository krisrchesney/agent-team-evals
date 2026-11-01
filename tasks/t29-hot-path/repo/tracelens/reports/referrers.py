"""Where visitors came from."""
from collections import Counter
from urllib.parse import urlparse


def host_of(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def top_referrers(events, n=10):
    """(host, count) for the referrers of view events, most first, ties by host."""
    counts = Counter()
    for e in events:
        ref = e.props.get("ref")
        if e.kind == "view" and ref:
            counts[host_of(ref)] += 1
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return rows if n is None else rows[:n]


def direct_share(events):
    views = [e for e in events if e.kind == "view"]
    if not views:
        return 0.0
    return sum(1 for e in views if not e.props.get("ref")) / len(views)


def campaign_counts(events):
    """utm_campaign -> views."""
    counts = Counter(e.props["utm_campaign"] for e in events if e.kind == "view" and "utm_campaign" in e.props)
    return dict(sorted(counts.items()))

"""A plain-text summary of one pipeline result, for email digests."""
from ..timeutil import humanize


def format_summary(result, title="Traffic summary"):
    lines = [title, "=" * len(title), ""]
    lines.append(f"Events:     {result['events']:,}")
    lines.append(f"Duplicates: {result['duplicates']:,}")
    lines.append(f"Sessions:   {result['sessions']:,}")
    lines.append(f"Bounce:     {result['bounce_rate']:.1%}")
    if result["top_pages"]:
        lines += ["", "Top pages"]
        width = max(len(page) for page, _ in result["top_pages"])
        for page, count in result["top_pages"]:
            lines.append(f"  {page:<{width}}  {count:>8,}")
    if result["funnel"]:
        lines += ["", "Funnel"]
        first = result["funnel"][0] or 1
        for i, users in enumerate(result["funnel"], start=1):
            lines.append(f"  step {i}: {users:,} ({users / first:.0%})")
    return "\n".join(lines) + "\n"


def session_lengths(sessions, buckets=(60_000, 300_000, 1_800_000)):
    """How many sessions lasted up to each bound, plus the rest, as labelled counts."""
    labels = [f"<= {humanize(b)}" for b in buckets] + [f"> {humanize(buckets[-1])}"]
    counts = [0] * len(labels)
    for s in sessions:
        for i, bound in enumerate(buckets):
            if s.duration_ms <= bound:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return dict(zip(labels, counts))


def one_line(result):
    return (f"{result['events']} events, {result['sessions']} sessions, "
            f"{len(result['top_pages'])} top pages")


def compare(before, after):
    """Change in the headline numbers between two results, as {name: (before, after, delta)}."""
    names = ("events", "duplicates", "sessions")
    return {n: (before[n], after[n], after[n] - before[n]) for n in names}

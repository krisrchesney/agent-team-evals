"""Page popularity."""


def top_pages(events, n=10, unique_users=False):
    """The `n` most viewed pages as (page, count), most viewed first, ties by page name.

    Only "view" events count. With `unique_users` a page counts each user once. `n=None` returns every
    page.
    """
    counts = []  # [page, count, viewers]
    for event in events:
        if event.kind != "view":
            continue
        for entry in counts:
            if entry[0] == event.page:
                break
        else:
            entry = [event.page, 0, []]
            counts.append(entry)
        if unique_users:
            if event.user not in entry[2]:
                entry[2].append(event.user)
                entry[1] += 1
        else:
            entry[1] += 1
    counts.sort(key=lambda e: (-e[1], e[0]))
    rows = [(e[0], e[1]) for e in counts]
    return rows if n is None else rows[:n]


def page_share(events, page):
    """The share of all views that went to `page`."""
    views = [e for e in events if e.kind == "view"]
    if not views:
        return 0.0
    return sum(1 for e in views if e.page == page) / len(views)


def entry_pages(sessions):
    """How many sessions started on each page, as (page, count) most first."""
    counts = {}
    for s in sessions:
        counts[s.pages[0]] = counts.get(s.pages[0], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

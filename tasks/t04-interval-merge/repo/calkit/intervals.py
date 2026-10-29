"""Merge busy calendar intervals and find the free time between them."""


def merge(intervals):
    """Merge overlapping [start, end] intervals into busy blocks."""
    merged = []
    for iv in intervals:
        if merged and iv[0] < merged[-1][1]:
            merged[-1][1] = iv[1]
        else:
            merged.append(iv)
    return merged


def free_slots(busy, window_start, window_end):
    """Return the free [start, end] gaps inside [window_start, window_end)."""
    slots = []
    cursor = window_start
    for start, end in merge(busy):
        if end <= window_start or start >= window_end:
            continue
        start = max(start, window_start)
        end = min(end, window_end)
        if start > cursor:
            slots.append([cursor, start])
        cursor = max(cursor, end)
    return slots

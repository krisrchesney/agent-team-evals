"""Merge busy calendar intervals and find the free time between them."""


def merge(intervals):
    """Merge overlapping or touching [start, end] intervals into busy blocks."""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
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
    if cursor < window_end:
        slots.append([cursor, window_end])
    return slots

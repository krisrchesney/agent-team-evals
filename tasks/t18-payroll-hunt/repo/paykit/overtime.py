"""Splitting a week of shifts into regular and overtime minutes."""

OVERTIME_AFTER = 40 * 60  # paid minutes in one week


def allocate(week_shifts):
    """Walk one employee's shifts of one week in time order, from the first minute of the week.

    Returns a list of (shift, regular_minutes, overtime_minutes). Paid minutes beyond the first
    OVERTIME_AFTER of the week are overtime; a shift that crosses the limit is split.
    """
    ordered = sorted(week_shifts, key=lambda shift: (shift.start, shift.day))
    worked = 0
    parts = []
    for shift in ordered:
        minutes = shift.paid_minutes
        regular = max(0, min(minutes, OVERTIME_AFTER - worked))
        parts.append((shift, regular, minutes - regular))
        worked += minutes
    return parts

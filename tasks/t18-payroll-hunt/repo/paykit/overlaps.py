"""Finding shifts of one employee that overlap in time."""
from .timeutil import MINUTES_PER_DAY


def _span(shift):
    """Absolute (begin, end) in minutes; an overnight shift runs into the next day."""
    begin = shift.day.toordinal() * MINUTES_PER_DAY + shift.start
    return begin, begin + shift.duration


def find_overlaps(shifts):
    """Pairs (a, b) of shifts of the same employee that share some time, with a before b in the
    list. A shift that ends exactly when another starts does not overlap it."""
    pairs = []
    for index, first in enumerate(shifts):
        first_begin, first_end = _span(first)
        for second in shifts[index + 1:]:
            if second.employee_id != first.employee_id:
                continue
            second_begin, second_end = _span(second)
            if first_begin < second_end and second_begin < first_end:
                pairs.append((first, second))
    return pairs

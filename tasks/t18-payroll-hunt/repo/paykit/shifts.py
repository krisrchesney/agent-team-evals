"""One worked shift and how much of it is paid."""
from .rounding import round_quarter_hour
from .timeutil import MINUTES_PER_DAY, parse_day, parse_hhmm

# A shift longer than this many minutes must include a break of at least AUTO_BREAK minutes.
LONG_SHIFT = 360
AUTO_BREAK = 30


class Shift:
    def __init__(self, employee_id, day, start, end, break_min=0):
        self.employee_id = employee_id
        self.day = parse_day(day)
        self.start = parse_hhmm(start)
        self.end = parse_hhmm(end)
        if self.start == self.end:
            raise ValueError("a shift cannot start and end at the same time")
        if not isinstance(break_min, int) or isinstance(break_min, bool) or break_min < 0:
            raise ValueError("break_min must be a non-negative int")
        if break_min >= self.duration:
            raise ValueError("the break must be shorter than the shift")
        self.break_min = break_min

    @property
    def duration(self):
        """Minutes between start and end on the clock; an earlier end means the next day."""
        if self.end > self.start:
            return self.end - self.start
        return self.end + MINUTES_PER_DAY - self.start

    @property
    def unpaid_break(self):
        """The break that is deducted: long shifts get at least the automatic break."""
        if self.duration >= LONG_SHIFT and self.break_min < AUTO_BREAK:
            return AUTO_BREAK
        return self.break_min

    @property
    def paid_minutes(self):
        """Paid minutes: duration minus the unpaid break, rounded to the nearest quarter hour."""
        return round_quarter_hour(self.duration - self.unpaid_break)

    def __repr__(self):
        return f"Shift({self.employee_id!r}, {self.day.isoformat()}, {self.start}-{self.end})"

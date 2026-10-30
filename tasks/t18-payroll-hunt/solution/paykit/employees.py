"""Employees and their hourly rates, which can change over time."""
from .timeutil import parse_day


class Employee:
    def __init__(self, emp_id, name, rates):
        """`rates` is a list of (effective_day, cents_per_hour) pairs, in any order."""
        if not isinstance(emp_id, str) or not emp_id:
            raise ValueError("employee id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("employee name must be a non-empty string")
        entries = []
        for effective, cents in rates:
            if not isinstance(cents, int) or isinstance(cents, bool) or cents <= 0:
                raise ValueError("a rate must be a positive int of cents per hour")
            entries.append((parse_day(effective), cents))
        if not entries:
            raise ValueError("an employee needs at least one rate")
        self.id = emp_id
        self.name = name
        self._rates = sorted(entries, key=lambda entry: entry[0])

    def rate_on(self, day):
        """Cents per hour in effect on `day`: the rate with the latest effective day <= `day`."""
        day = parse_day(day)
        current = None
        for effective, cents in self._rates:
            if effective <= day:
                current = cents
        if current is None:
            raise ValueError(f"{self.id}: no rate in effect on {day.isoformat()}")
        return current

"""Weekly pay for every employee who worked."""
from .overtime import allocate
from .weeks import week_key, week_start


class PayRow:
    """The pay of one employee over all the shifts given."""

    def __init__(self, employee_id, name, regular_minutes, overtime_minutes, gross_cents):
        self.employee_id = employee_id
        self.name = name
        self.regular_minutes = regular_minutes
        self.overtime_minutes = overtime_minutes
        self.gross_cents = gross_cents

    def __repr__(self):
        return f"PayRow({self.employee_id!r}, {self.gross_cents})"


class WeekRow:
    """The pay of one employee for one pay week."""

    def __init__(self, employee_id, name, week_start, regular_minutes, overtime_minutes,
                 gross_cents):
        self.employee_id = employee_id
        self.name = name
        self.week_start = week_start  # the Monday, as a date
        self.regular_minutes = regular_minutes
        self.overtime_minutes = overtime_minutes
        self.gross_cents = gross_cents

    def __repr__(self):
        return f"WeekRow({self.employee_id!r}, {self.week_start.isoformat()}, {self.gross_cents})"


def regular_pay(rate, minutes):
    """Cents for `minutes` at `rate` cents per hour, halves rounding up."""
    return round(rate * minutes / 60)


def overtime_pay(rate, minutes):
    """Cents for `minutes` at one and a half times `rate`, halves rounding up."""
    return round(rate * minutes * 3 / 120)


def _group_by_week(shifts, known_ids):
    grouped = {}
    for shift in shifts:
        if shift.employee_id not in known_ids:
            raise ValueError(f"unknown employee {shift.employee_id!r}")
        weeks = grouped.setdefault(shift.employee_id, {})
        weeks.setdefault(week_key(shift.day), []).append(shift)
    return grouped


def weekly_breakdown(employees, shifts):
    """One WeekRow per employee and pay week with shifts, ordered by employee name (ignoring
    case), then employee id, then week."""
    by_id = {employee.id: employee for employee in employees}
    rows = []
    for emp_id, weeks in _group_by_week(shifts, by_id).items():
        employee = by_id[emp_id]
        for week_shifts in weeks.values():
            regular_minutes = overtime_minutes = gross = 0
            for shift, regular, overtime in allocate(week_shifts):
                rate = employee.rate_on(shift.day)
                gross += regular_pay(rate, regular) + overtime_pay(rate, overtime)
                regular_minutes += regular
                overtime_minutes += overtime
            rows.append(WeekRow(emp_id, employee.name, week_start(week_shifts[0].day),
                                regular_minutes, overtime_minutes, gross))
    rows.sort(key=lambda row: (row.name.casefold(), row.employee_id, row.week_start))
    return rows


def compute_payroll(employees, shifts):
    """One PayRow per employee that has shifts, ordered by name (ignoring case), then id."""
    totals = {}
    for week in weekly_breakdown(employees, shifts):
        row = totals.get(week.employee_id)
        if row is None:
            row = totals[week.employee_id] = PayRow(week.employee_id, week.name, 0, 0, 0)
        row.regular_minutes += week.regular_minutes
        row.overtime_minutes += week.overtime_minutes
        row.gross_cents += week.gross_cents
    return list(totals.values())

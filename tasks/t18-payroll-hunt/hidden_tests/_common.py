"""Shared helpers for the hidden t18 tests."""
import datetime

from paykit import Employee, Shift

HEADER = "employee_id,day,start,end,break_min"


def emp(emp_id="e1", name="Ann Lee", rates=(("2024-01-01", 2000),)):
    return Employee(emp_id, name, list(rates))


def sh(day, start, end, brk=0, emp_id="e1"):
    return Shift(emp_id, day, start, end, brk)


def day(text):
    return datetime.date.fromisoformat(text)


def add_days(text, n):
    return (day(text) + datetime.timedelta(days=n)).isoformat()


def weekdays(monday, start="08:00", end="17:00", brk=60, emp_id="e1"):
    """Monday to Friday shifts that are 480 paid minutes each (2400 in all)."""
    return [sh(add_days(monday, n), start, end, brk, emp_id) for n in range(5)]


def end_after(minutes, start_minutes=9 * 60):
    """The HH:MM that is `minutes` after 09:00 (same day)."""
    return "%02d:%02d" % divmod(start_minutes + minutes, 60)

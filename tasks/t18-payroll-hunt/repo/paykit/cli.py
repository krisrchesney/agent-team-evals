"""Command line entry: read shifts and employees from files and print the payroll report."""
import json
import sys

from .employees import Employee
from .loader import load_shifts
from .overlaps import find_overlaps
from .payroll import compute_payroll
from .report import render_text

USAGE = "usage: paykit SHIFTS.csv EMPLOYEES.json"


def _parse_args(argv):
    if len(argv) != 2:
        raise ValueError(USAGE)
    return argv[0], argv[1]


def _load_employees(path):
    with open(path, encoding="utf-8") as handle:
        records = json.load(handle)
    return [Employee(rec["id"], rec["name"], [tuple(rate) for rate in rec["rates"]])
            for rec in records]


def main(argv):
    """Run the tool; returns the exit status (0 ok, 2 for any error)."""
    try:
        shifts_path, employees_path = _parse_args(argv)
        with open(shifts_path, encoding="utf-8") as handle:
            shifts = load_shifts(handle.read())
        employees = _load_employees(employees_path)
        for first, second in find_overlaps(shifts):
            print(f"warning: overlapping shifts for {first.employee_id} on "
                  f"{first.day.isoformat()}", file=sys.stderr)
        text = render_text(compute_payroll(employees, shifts))
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    return 0

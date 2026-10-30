"""Command line entry: read shifts and employees from files and print the payroll report."""
import json
import sys

from .employees import Employee
from .loader import load_shifts
from .overlaps import find_overlaps
from .payroll import compute_payroll
from .report import render

USAGE = "usage: paykit SHIFTS.csv EMPLOYEES.json [--format text|csv]"


def _parse_args(argv):
    args = list(argv)
    fmt = "text"
    if "--format" in args:
        index = args.index("--format")
        if index + 1 >= len(args):
            raise ValueError(USAGE)
        fmt = args[index + 1]
        del args[index:index + 2]
    if len(args) != 2:
        raise ValueError(USAGE)
    return args[0], args[1], fmt


def _load_employees(path):
    with open(path, encoding="utf-8") as handle:
        records = json.load(handle)
    return [Employee(rec["id"], rec["name"], [tuple(rate) for rate in rec["rates"]])
            for rec in records]


def main(argv):
    """Run the tool; returns the exit status (0 ok, 2 for any error)."""
    try:
        shifts_path, employees_path, fmt = _parse_args(argv)
        with open(shifts_path, encoding="utf-8") as handle:
            shifts = load_shifts(handle.read())
        employees = _load_employees(employees_path)
        for first, second in find_overlaps(shifts):
            print(f"warning: overlapping shifts for {first.employee_id} on "
                  f"{first.day.isoformat()}", file=sys.stderr)
        text = render(compute_payroll(employees, shifts), fmt)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    return 0

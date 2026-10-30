"""Reading shifts from CSV text."""
import csv
import io

from .shifts import Shift

HEADER = ["employee_id", "day", "start", "end", "break_min"]


def _parse_break(text):
    if text == "":
        return 0
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"bad break_min {text!r}") from None


def load_shifts(text):
    """Parse CSV text into Shift objects.

    The first non-blank line is the header. Errors are reported as ValueError('line N: ...')
    where N counts the physical lines of the text from 1, blank lines included.
    """
    reader = csv.reader(io.StringIO(text))
    shifts = []
    seen_header = False
    for fields in reader:
        fields = [field.strip() for field in fields]
        if not any(fields):
            continue
        number = reader.line_num
        if not seen_header:
            if fields != HEADER:
                raise ValueError(f"line {number}: expected the header {','.join(HEADER)}")
            seen_header = True
            continue
        if len(fields) not in (4, 5):
            raise ValueError(f"line {number}: expected 4 or 5 fields, got {len(fields)}")
        emp_id, day, start, end = fields[:4]
        try:
            shifts.append(Shift(emp_id, day, start, end, _parse_break(fields[4] if len(fields) == 5 else "")))
        except ValueError as exc:
            raise ValueError(f"line {number}: {exc}") from None
    return shifts

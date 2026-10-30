"""Parse lines of the form `<ts> <LEVEL> <message>`, e.g. `1700000000 WARN disk almost full`."""
from .errors import ParseError
from .record import LEVELS, Record


def parse_line(line, number=0):
    parts = line.split(None, 2)
    if len(parts) < 3:
        raise ParseError(f"line {number}: expected '<ts> <LEVEL> <message>'")
    ts_text, level, msg = parts
    try:
        ts = int(ts_text)
    except ValueError:
        raise ParseError(f"line {number}: bad timestamp '{ts_text}'") from None
    level = level.upper()
    if level not in LEVELS:
        raise ParseError(f"line {number}: bad level '{parts[1]}'")
    return Record(ts, level, msg.strip())


def parse_lines(lines):
    """Yield a Record per non-blank line. Blank lines are skipped but still count in line numbers."""
    for number, line in enumerate(lines, start=1):
        if line.strip():
            yield parse_line(line, number)

"""Parse lines of the form `<ts> <LEVEL> <message> [| key=value ...]`,
e.g. `1700000000 WARN disk almost full | host=db1`."""
import re

from .errors import ParseError
from .record import LEVELS, Record

_FIELD = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("[^"]*"|[^\s"]\S*)')


def parse_fields(text):
    """Parse the part after ` | ` into an ordered dict, or return None if it is malformed."""
    text = text.strip()
    fields, pos = {}, 0
    while pos < len(text):
        m = _FIELD.match(text, pos)
        if not m or (m.end() < len(text) and not text[m.end()].isspace()):
            return None
        value = m.group(2)
        fields[m.group(1)] = value[1:-1] if value.startswith('"') else value
        pos = m.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
    return fields


def parse_line(line, number=0):
    parts = line.split(None, 2)
    if len(parts) < 3:
        raise ParseError(f"line {number}: expected '<ts> <LEVEL> <message>'")
    ts_text, level, rest = parts
    try:
        ts = int(ts_text)
    except ValueError:
        raise ParseError(f"line {number}: bad timestamp '{ts_text}'") from None
    level = level.upper()
    if level not in LEVELS:
        raise ParseError(f"line {number}: bad level '{parts[1]}'")
    msg, sep, field_text = rest.partition(" | ")
    fields = parse_fields(field_text) if sep else {}
    if fields is None:
        raise ParseError(f"line {number}: bad fields '{field_text.strip()}'")
    return Record(ts, level, msg.strip(), fields)


def parse_lines(lines, on_error=None):
    """Yield a Record per non-blank line. Blank lines are skipped but still count in line numbers.
    A malformed line raises ParseError, or goes to `on_error(error)` and is skipped if that is given."""
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            yield parse_line(line, number)
        except ParseError as e:
            if on_error is None:
                raise
            on_error(e)

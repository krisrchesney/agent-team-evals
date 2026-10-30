"""The built-in renderers. Each takes `(columns, rows)` and returns a string."""
import json


def _csv_cell(value):
    if value is None:
        text = ""
    elif value is True:
        text = "true"
    elif value is False:
        text = "false"
    elif isinstance(value, float):
        text = ("%.2f" % value).rstrip("0").rstrip(".")
    else:
        text = str(value)
    if any(ch in text for ch in ',"\r\n') or text != text.strip(" "):
        text = '"' + text.replace('"', '""') + '"'
    return text


def render_csv(columns, rows):
    if not columns:
        return ""
    lines = [",".join(_csv_cell(name) for name in columns)]
    lines += [",".join(_csv_cell(value) for value in row) for row in rows]
    return "\n".join(lines) + "\n"


def render_json(columns, rows):
    return json.dumps([dict(zip(columns, row)) for row in rows], indent=2, ensure_ascii=False)


def _table_cell(value):
    if value is None:
        return "-"
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if isinstance(value, float):
        return "%.2f" % value
    return str(value)


def _is_numeric_column(rows, index):
    values = [row[index] for row in rows if row[index] is not None]
    return bool(values) and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)


def render_table(columns, rows):
    if not columns:
        return "(no data)"
    cells = [[_table_cell(value) for value in row] for row in rows]
    right = [_is_numeric_column(rows, i) for i in range(len(columns))]
    widths = [max([len(str(name))] + [len(row[i]) for row in cells])
              for i, name in enumerate(columns)]

    def line(items):
        parts = [item.rjust(w) if right[i] else item.ljust(w)
                 for i, (item, w) in enumerate(zip(items, widths))]
        return "  ".join(parts).rstrip()

    lines = [line([str(name) for name in columns]), "  ".join("-" * w for w in widths)]
    return "\n".join(lines + [line(row) for row in cells])

"""Export records as CSV, JSON or a text table."""
import json


def export(records, fmt, columns=None, sort_by=None, descending=False, limit=None):
    if fmt not in ("csv", "json", "table"):
        raise ValueError("unknown format %r" % (fmt,))

    # which columns, in which order
    if columns is None:
        cols = []
        for rec in records:
            for key in rec:
                if key not in cols:
                    cols.append(key)
    else:
        cols = list(columns)
        seen = set()
        for c in cols:
            if c in seen:
                raise ValueError("duplicate column %r" % (c,))
            seen.add(c)
    if sort_by is not None and sort_by not in cols:
        raise ValueError("unknown sort column %r" % (sort_by,))
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 0):
        raise ValueError("limit must be a non-negative int")

    # one list of raw values per record
    rows = [[rec.get(c) for c in cols] for rec in records]

    # ordering: None always last, equal values keep their input order
    if sort_by is not None:
        i = cols.index(sort_by)
        present = [r for r in rows if r[i] is not None]
        absent = [r for r in rows if r[i] is None]

        def rank(v):
            if isinstance(v, (int, float)):
                return (0, v)
            return (1, str(v))

        present.sort(key=lambda r: rank(r[i]), reverse=descending)
        rows = present + absent
    if limit is not None:
        rows = rows[:limit]

    if fmt == "csv":
        if not cols:
            return ""

        def cell(v):
            if v is None:
                s = ""
            elif v is True:
                s = "true"
            elif v is False:
                s = "false"
            elif isinstance(v, float):
                s = ("%.2f" % v).rstrip("0").rstrip(".")
            else:
                s = str(v)
            if any(ch in s for ch in ',"\r\n') or s != s.strip(" "):
                s = '"' + s.replace('"', '""') + '"'
            return s

        out = [",".join(cell(c) for c in cols)]
        for r in rows:
            out.append(",".join(cell(v) for v in r))
        return "\n".join(out) + "\n"

    if fmt == "json":
        return json.dumps([dict(zip(cols, r)) for r in rows], indent=2, ensure_ascii=False)

    # fmt == "table"
    if not cols:
        return "(no data)"

    def tcell(v):
        if v is None:
            return "-"
        if v is True:
            return "yes"
        if v is False:
            return "no"
        if isinstance(v, float):
            return "%.2f" % v
        return str(v)

    cells = [[tcell(v) for v in r] for r in rows]
    numeric = []
    for i in range(len(cols)):
        vals = [r[i] for r in rows if r[i] is not None]
        numeric.append(bool(vals) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals))
    widths = [max([len(str(c))] + [len(row[i]) for row in cells]) for i, c in enumerate(cols)]

    def line(items):
        parts = [it.rjust(w) if numeric[i] else it.ljust(w)
                 for i, (it, w) in enumerate(zip(items, widths))]
        return "  ".join(parts).rstrip()

    out = [line([str(c) for c in cols]), "  ".join("-" * w for w in widths)]
    out += [line(row) for row in cells]
    return "\n".join(out)

"""Select, order and limit records: the layer between the data and the renderers."""


def _pick_columns(records, columns):
    if columns is None:
        picked = []
        for record in records:
            for key in record:
                if key not in picked:
                    picked.append(key)
        return picked
    picked = list(columns)
    seen = set()
    for name in picked:
        if name in seen:
            raise ValueError("duplicate column %r" % (name,))
        seen.add(name)
    return picked


def _check_limit(limit):
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 0):
        raise ValueError("limit must be a non-negative int")


def _rank(value):
    """Numbers compare as numbers and sort before everything else, which compares as text."""
    if isinstance(value, (int, float)):
        return (0, value)
    return (1, str(value))


def _order(rows, index, descending):
    present = [row for row in rows if row[index] is not None]
    absent = [row for row in rows if row[index] is None]
    present.sort(key=lambda row: _rank(row[index]), reverse=descending)
    return present + absent


def prepare(records, columns=None, sort_by=None, descending=False, limit=None):
    """Return `(columns, rows)`: the chosen column names and one list of raw values per record,
    sorted and limited as asked."""
    names = _pick_columns(records, columns)
    if sort_by is not None and sort_by not in names:
        raise ValueError("unknown sort column %r" % (sort_by,))
    _check_limit(limit)
    rows = [[record.get(name) for name in names] for record in records]
    if sort_by is not None:
        rows = _order(rows, names.index(sort_by), descending)
    if limit is not None:
        rows = rows[:limit]
    return names, rows

"""Group rows by one column and total another."""


def group_sum(rows, key, value):
    totals = {}
    for row in rows:
        group = row[key]
        totals[group] = totals.get(group, 0.0) + float(row[value])
    return totals

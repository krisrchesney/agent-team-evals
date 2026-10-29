"""Group rows by one column and aggregate another."""

AGGS = ("sum", "count", "mean", "min", "max")


class ReportError(Exception):
    """A problem with the input that the CLI reports as `csvreport: error: ...`."""


def filter_rows(rows, where):
    """Keep rows matching every (column, value) pair in `where`."""
    return [r for r in rows if all(r[col] == want for col, want in where)]


def aggregate(rows, key, value, agg, path="<input>"):
    """Return {group: result}. Result is int for count, float or None otherwise."""
    groups = {}
    for row in rows:
        nums = groups.setdefault(row[key], [])
        if agg == "count":
            nums.append(1)
            continue
        cell = row[value]
        if cell == "":
            continue
        try:
            nums.append(float(cell))
        except ValueError:
            raise ReportError(f"{path}:{row.line}: bad number '{cell}' in column '{value}'")
    results = {}
    for group, nums in groups.items():
        if agg == "count":
            results[group] = len(nums)
        elif agg == "sum":
            results[group] = float(sum(nums))
        elif not nums:
            results[group] = None
        elif agg == "mean":
            results[group] = sum(nums) / len(nums)
        else:
            results[group] = min(nums) if agg == "min" else max(nums)
    return results


def group_sum(rows, key, value):
    return aggregate(rows, key, value, "sum")

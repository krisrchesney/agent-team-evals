"""Read a CSV file into a list of row dicts keyed by header name."""
import csv


class Row(dict):
    """A row dict that also remembers its 1-based line number in the file."""

    line = 0


def read_table(path, delimiter=","):
    """Return (header, rows). Whitespace is stripped; all-empty rows are skipped."""
    header, rows = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for cells in reader:
            cells = [c.strip() for c in cells]
            if not any(cells):
                continue
            if not header:
                header = cells
                continue
            cells += [""] * (len(header) - len(cells))
            row = Row(zip(header, cells))
            row.line = reader.line_num
            rows.append(row)
    return header, rows


def read_rows(path, delimiter=","):
    return read_table(path, delimiter)[1]

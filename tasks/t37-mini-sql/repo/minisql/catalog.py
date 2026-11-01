"""CSV tables. `Catalog(directory).table(name)` reads `<name>.csv` from the directory (the file name is matched
ignoring case) with the csv module, UTF-8 (a BOM is accepted).

- The first row is the header; names are kept as spelled there. Duplicate names (ignoring case) are a CatalogError.
- Every data row must have exactly as many fields as the header, else CatalogError.
- An empty cell is NULL (None).
- A column is typed from all its non-empty cells: int if every one matches -?[0-9]+, else float if every one matches
  -?[0-9]+(.[0-9]+)?, else str (cells stay as text). Leading zeros are not kept: "007" in an int column is 7.
"""
import csv
import os
import re
from collections import namedtuple

from .errors import CatalogError

Table = namedtuple("Table", "name columns rows")  # columns: list of header names; rows: list of tuples

INT_RE = re.compile(r"^-?[0-9]+$")
FLOAT_RE = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")


class Catalog:
    def __init__(self, directory):
        self.directory = directory
        self._cache = {}

    def table(self, name):
        key = name.lower()
        if key not in self._cache:
            self._cache[key] = self._load(key)
        return self._cache[key]

    def _load(self, key):
        path = None
        if os.path.isdir(self.directory):
            for fname in sorted(os.listdir(self.directory)):
                if fname.lower() == key + ".csv":
                    path = os.path.join(self.directory, fname)
                    break
        if path is None:
            raise CatalogError("no such table: %s" % key)
        with open(path, encoding="utf-8-sig", newline="") as fh:
            raw = list(csv.reader(fh))
        if not raw:
            raise CatalogError("%s.csv is empty" % key)
        header, body = raw[0], raw[1:]
        if len({h.lower() for h in header}) != len(header):
            raise CatalogError("duplicate column names in %s.csv" % key)
        for n, row in enumerate(body, 2):
            if len(row) != len(header):
                raise CatalogError("%s.csv line %d has %d fields, expected %d" % (key, n, len(row), len(header)))
        convert = []
        for i in range(len(header)):
            cells = [row[i] for row in body if row[i] != ""]
            if all(INT_RE.match(c) for c in cells):
                convert.append(int)
            elif all(FLOAT_RE.match(c) for c in cells):
                convert.append(float)
            else:
                convert.append(str)
        rows = [tuple(None if cell == "" else convert[i](cell) for i, cell in enumerate(row)) for row in body]
        return Table(key, header, rows)

"""Running a Query against a Catalog. See docs/SPEC.md."""
from collections import namedtuple

Result = namedtuple("Result", "columns rows")  # columns: list of names; rows: list of tuples


def execute(query, catalog):
    raise NotImplementedError

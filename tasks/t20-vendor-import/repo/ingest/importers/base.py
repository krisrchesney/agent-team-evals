"""The shared part of every importer (docs/IMPORTERS.md)."""
import csv
import io

from .. import dates
from ..config import vendor_settings
from ..records import ImportResult, RowError


class RowProblem(Exception):
    """Raised by parse_row for a row that cannot be loaded. `code` is from docs/IMPORTERS.md."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class BaseImporter:
    vendor = None
    delimiter = ","

    def __init__(self, settings=None):
        self.settings = settings if settings is not None else vendor_settings(self.vendor)

    def default_due(self, invoice_date):
        return dates.add_days(invoice_date, self.settings["terms_days"])

    def parse_row(self, row):
        raise NotImplementedError

    def parse(self, text):
        result = ImportResult(vendor=self.vendor)
        if text.startswith("﻿"):
            text = text[1:]
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=self.delimiter)
        seen = set()
        for row in reader:
            start = reader.line_num   # physical line the row ends on (header = line 1)
            if not any((value or "").strip() for value in row.values()):
                continue
            try:
                record = self.parse_row(row)
            except RowProblem as problem:
                result.errors.append(RowError(start, problem.code))
                continue
            if record is None:
                continue
            key = (record.invoice_id, record.line_no)
            if key in seen:
                result.errors.append(RowError(start, "duplicate_line"))
                continue
            seen.add(key)
            result.records.append(record)
        return result


def required(row, column):
    """The stripped value of a column, or RowProblem("missing_field") if it is empty or absent."""
    value = (row.get(column) or "").strip()
    if not value:
        raise RowProblem("missing_field")
    return value


def optional(row, column):
    return (row.get(column) or "").strip()


def whole_number(text):
    if not text.isdigit() or int(text) < 1:
        raise RowProblem("bad_qty")
    return int(text)

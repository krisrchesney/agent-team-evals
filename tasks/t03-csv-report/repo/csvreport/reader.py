"""Read a CSV file into a list of row dicts keyed by header name."""
import csv


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

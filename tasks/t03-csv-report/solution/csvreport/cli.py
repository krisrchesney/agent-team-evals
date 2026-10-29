"""Command line: python -m csvreport FILE --group-by COL [--agg AGG --value COL | --sum COL]"""
import argparse
import sys

from .aggregate import AGGS, ReportError, aggregate, filter_rows
from .reader import read_table
from .render import render


def build_parser():
    p = argparse.ArgumentParser(prog="csvreport", description="Group CSV rows and aggregate a column.")
    p.add_argument("path")
    p.add_argument("--group-by", required=True, metavar="COL")
    p.add_argument("--sum", metavar="COL", help="shorthand for --agg sum --value COL")
    p.add_argument("--agg", choices=AGGS)
    p.add_argument("--value", metavar="COL")
    p.add_argument("--where", action="append", default=[], metavar="COL=VALUE")
    p.add_argument("--delimiter", default=",", metavar="CHAR")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.sum is not None:
        if args.agg is not None or args.value is not None:
            parser.error("--sum cannot be combined with --agg or --value")
        agg, value = "sum", args.sum
    else:
        agg, value = args.agg or "sum", args.value
    if agg == "count":
        value = None
    elif value is None:
        parser.error(f"--agg {agg} needs --value")
    where = []
    for item in args.where:
        col, sep, want = item.partition("=")
        if not sep:
            parser.error(f"--where needs COL=VALUE, got {item!r}")
        where.append((col, want))
    try:
        header, rows = read_table(args.path, args.delimiter)
        needed = [args.group_by] + ([value] if value else []) + [col for col, _ in where]
        for col in needed:
            if col not in header:
                raise ReportError(f"no column '{col}'")
        results = aggregate(filter_rows(rows, where), args.group_by, value, agg, args.path)
    except ReportError as e:
        print(f"csvreport: error: {e}", file=sys.stderr)
        return 2
    label = "count" if agg == "count" else f"{agg}_{value}"
    print(render(results, args.group_by, label))
    return 0

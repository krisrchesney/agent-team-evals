"""Command line: python -m salesrep FILE [options]"""
import argparse
import sys

from .aggregate import DIMENSIONS
from .dates import parse_iso
from .errors import ParseError, UsageError
from .report import build_report, skipped_block


def build_parser():
    p = argparse.ArgumentParser(prog="salesrep", description="Revenue report from a sales CSV.")
    p.add_argument("path")
    p.add_argument("--json", action="store_true", help="same as --format json")
    p.add_argument("--format", choices=("table", "csv", "json"), default=None)
    p.add_argument("--by", choices=DIMENSIONS, default="region")
    p.add_argument("--top", metavar="N")
    p.add_argument("--title", metavar="TEXT")
    p.add_argument("--from", dest="date_from", metavar="DATE")
    p.add_argument("--to", dest="date_to", metavar="DATE")
    p.add_argument("--strict", action="store_true", help="exit 1 if any row was skipped")
    return p


def _date(text, option):
    if text is None:
        return None
    try:
        return parse_iso(text)
    except ValueError:
        raise UsageError(f"bad date '{text}' for {option}") from None


def _options(args):
    if args.json and args.format is not None:
        raise UsageError("use either --json or --format")
    top = None
    if args.top is not None:
        try:
            top = int(args.top)
        except ValueError:
            top = 0
        if top < 1:
            raise UsageError("--top must be a whole number of at least 1")
    date_from, date_to = _date(args.date_from, "--from"), _date(args.date_to, "--to")
    if date_from and date_to and date_from > date_to:
        raise UsageError("--from is after --to")
    fmt = "json" if args.json else (args.format or "table")
    return dict(by=args.by, top=top, title=args.title, fmt=fmt, date_from=date_from, date_to=date_to)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        options = _options(args)
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
        out, issues = build_report(text, **options)
    except (ParseError, UsageError) as e:
        print(f"salesrep: error: {e}", file=sys.stderr)
        return 2
    print(out)
    if issues and options["fmt"] != "table":
        print(skipped_block(issues), file=sys.stderr)
    return 1 if issues and args.strict else 0

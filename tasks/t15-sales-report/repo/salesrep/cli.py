"""Command line: python -m salesrep FILE"""
import argparse
import sys

from .errors import ParseError, UsageError
from .report import build_report


def build_parser():
    p = argparse.ArgumentParser(prog="salesrep", description="Revenue report from a sales CSV.")
    p.add_argument("path")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
        out, _issues = build_report(text, as_json=args.json)
    except (ParseError, UsageError) as e:
        print(f"salesrep: error: {e}", file=sys.stderr)
        return 2
    print(out)
    return 0

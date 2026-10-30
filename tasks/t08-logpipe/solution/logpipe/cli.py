"""Command line: python -m logpipe FILE [--filter SPEC]... [--transform SPEC]... [--format NAME]
[--lenient] [--stats]"""
import argparse
import sys

from .errors import ConfigError, ParseError
from .pipeline import run_pipeline


def build_parser():
    p = argparse.ArgumentParser(prog="logpipe", description="Filter and reformat a log file.")
    p.add_argument("path")
    p.add_argument("--filter", action="append", default=[], metavar="SPEC")
    p.add_argument("--transform", action="append", default=[], metavar="SPEC")
    p.add_argument("--format", default="text", metavar="NAME")
    p.add_argument("--lenient", action="store_true", help="skip malformed lines")
    p.add_argument("--stats", action="store_true", help="print counts to stderr when done")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    stats = {}
    try:
        with open(args.path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        out = run_pipeline(lines, args.filter, args.transform, args.format,
                           lenient=args.lenient, stats=stats)
    except (ParseError, ConfigError) as e:
        print(f"logpipe: error: {e}", file=sys.stderr)
        return 2
    for line in out:
        print(line)
    if args.stats:
        print(" ".join(f"{k}={stats[k]}" for k in ("read", "skipped", "filtered", "deduped", "emitted")),
              file=sys.stderr)
    return 0

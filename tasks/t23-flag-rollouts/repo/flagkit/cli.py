"""python -m flagkit FILE [--user ID] [--attr NAME=VALUE ...] [--at TIME]"""
import argparse
import json
import sys

from .client import FlagClient
from .clock import FixedClock
from .context import Context
from .errors import FlagError
from .loader import load_file
from .timeutil import parse_time


def main(argv=None, stdout=None):
    stdout = stdout or sys.stdout
    parser = argparse.ArgumentParser(prog="flagkit", description="Evaluate every flag in a file for one user.")
    parser.add_argument("file")
    parser.add_argument("--user")
    parser.add_argument("--attr", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--at", help="evaluate as of this time, e.g. 2026-03-02T09:00:00Z")
    args = parser.parse_args(argv)
    attrs = dict(item.split("=", 1) for item in args.attr if "=" in item)
    try:
        clock = FixedClock(parse_time("--at", "at", args.at)) if args.at else None
        client = FlagClient(load_file(args.file), clock=clock)
    except FlagError as err:
        print(f"flagkit: {err}", file=sys.stderr)
        return 2
    ctx = Context(user_id=args.user, attrs=attrs)
    out = {key: d.as_dict() for key, d in client.evaluate_all(ctx).items()}
    print(json.dumps(out, indent=2, sort_keys=True), file=stdout)
    return 0

"""`python -m tracelens.cli FILE`: run the pipeline on a log file and print a summary."""
import argparse
import sys

from . import pipeline
from .analysis.sessions import DEFAULT_GAP_MS
from .errors import TracelensError
from .ingest.logparse import parse_lines
from .timeutil import humanize


def build_parser():
    parser = argparse.ArgumentParser(prog="tracelens")
    parser.add_argument("log", help="path to a log file")
    parser.add_argument("--gap-minutes", type=int, default=DEFAULT_GAP_MS // 60000)
    parser.add_argument("--funnel", default="", help="comma-separated pages")
    parser.add_argument("--top", type=int, default=5)
    return parser


def main(argv=None, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        with open(args.log, encoding="utf-8") as handle:
            events, errors = parse_lines(handle)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    steps = [p for p in args.funnel.split(",") if p]
    try:
        result = pipeline.run(events, args.gap_minutes * 60000, steps, args.top)
    except TracelensError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    print(f"{result['events']} events ({result['duplicates']} duplicates, {len(errors)} unreadable lines)", file=out)
    print(f"{result['sessions']} sessions, bounce rate {result['bounce_rate']:.0%}", file=out)
    for page, count in result["top_pages"]:
        print(f"  {count:>6}  {page}", file=out)
    if steps:
        print("funnel: " + " > ".join(f"{p} {n}" for p, n in zip(steps, result["funnel"])), file=out)
    print(f"gap {humanize(args.gap_minutes * 60000)}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

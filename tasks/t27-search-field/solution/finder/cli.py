"""Command line: `python -m finder.cli search QUERY --docs docs.jsonl [--field title]...`"""
import argparse
import sys

from . import serializer
from .errors import FinderError
from .search import Searcher

FIELD_CHOICES = ("title", "body", "tags", "author")


def build_parser():
    parser = argparse.ArgumentParser(prog="finder")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="search a JSON-lines file of documents")
    search.add_argument("query")
    search.add_argument("--docs", required=True, help="path to a .jsonl file")
    search.add_argument("--field", action="append", choices=FIELD_CHOICES, dest="fields",
                        help="limit plain terms to this field (repeatable)")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--highlight", action="store_true")
    return parser


def main(argv=None, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        with open(args.docs, encoding="utf-8") as handle:
            docs = serializer.loads(handle.read())
        searcher = Searcher()
        for doc in docs:
            searcher.add(doc)
        result = searcher.search(args.query, fields=args.fields, limit=args.limit, highlight=args.highlight)
    except (FinderError, OSError) as exc:
        print(f"error: {getattr(exc, 'message', exc)}", file=sys.stderr)
        return 1
    print(f"{result.total} result(s)", file=out)
    for hit in result.hits:
        title = searcher.index.get(hit.id).title
        print(f"{hit.id}\t{hit.score:.3f}\t{title}", file=out)
        for name, text in hit.highlights.items():
            print(f"    {name}: {text}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

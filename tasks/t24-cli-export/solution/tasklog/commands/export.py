import csv
import io
import json
import os

from .. import atomicio
from ..errors import Conflict, IoFailure
from ..filters import add_filter_args, select
from ..model import FIELDS

NAME = "export"
HELP = "write the matching tasks to a CSV or JSON file"


def configure(parser):
    add_filter_args(parser)
    parser.add_argument("--output", required=True, metavar="PATH")
    parser.add_argument("--format", choices=("csv", "json"), default="csv")
    parser.add_argument("--force", action="store_true", help="replace the file if it exists")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def render(tasks, fmt):
    if fmt == "json":
        return json.dumps([t.to_dict() for t in tasks], indent=2, ensure_ascii=False) + "\n"
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(FIELDS)
    for task in tasks:
        writer.writerow(task.to_row())
    return buf.getvalue()


def run(args, con, store, clock):
    tasks = select(store, args)
    if os.path.exists(args.output) and not args.force:
        raise Conflict(f"{args.output} already exists (use --force)")
    try:
        atomicio.write_text(args.output, render(tasks, args.format))
    except OSError as err:
        raise IoFailure(f"cannot write {args.output}: {err.strerror or err}") from None
    con.say(f"exported {len(tasks)} tasks to {args.output}")
    con.emit({"command": NAME, "count": len(tasks), "format": args.format, "output": args.output})
    if not tasks:
        con.warn("no tasks match")

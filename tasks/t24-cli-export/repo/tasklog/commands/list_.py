from ..errors import UsageError
from ..filters import add_filter_args, select
from ..views import task_line

NAME = "list"
HELP = "list tasks"


def configure(parser):
    add_filter_args(parser)
    parser.add_argument("--limit", type=int, default=20, help="show at most this many (default 20)")
    parser.add_argument("--plain", action="store_true", help="one tab-separated line per task")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def run(args, con, store, clock):
    if args.limit < 1:
        raise UsageError("--limit must be at least 1")
    matching = select(store, args)
    shown = matching[:args.limit]
    for task in shown:
        con.say("\t".join(task.to_row()) if args.plain else task_line(task))
    con.emit({"command": NAME, "count": len(shown), "items": [t.to_dict() for t in shown]})
    if not matching:
        con.warn("no tasks match")
    elif len(matching) > len(shown):
        con.warn(f"showing {len(shown)} of {len(matching)} tasks")

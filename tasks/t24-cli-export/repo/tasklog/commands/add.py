from ..dates import parse_date, stamp
from ..errors import UsageError

NAME = "add"
HELP = "add a task"


def configure(parser):
    parser.add_argument("title")
    parser.add_argument("--project", default="inbox")
    parser.add_argument("--priority", type=int, default=2, help="1 (high) to 3 (low)")
    parser.add_argument("--tag", action="append", dest="tags", default=[])
    parser.add_argument("--due", metavar="DATE")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def run(args, con, store, clock):
    title = args.title.strip()
    if not title:
        raise UsageError("title must not be empty")
    if args.priority not in (1, 2, 3):
        raise UsageError("--priority must be 1, 2 or 3")
    project = args.project.strip()
    if not project:
        raise UsageError("--project must not be empty")
    due = str(parse_date(args.due, "--due")) if args.due is not None else None
    task = store.add(title=title, project=project, status="open", priority=args.priority,
                     created=stamp(clock.now()), tags=list(dict.fromkeys(args.tags)), due=due)
    store.save()
    con.say(f"added task #{task.id}: {task.title}")
    con.emit({"command": NAME, "item": task.to_dict()})

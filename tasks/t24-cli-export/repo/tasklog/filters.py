from .dates import parse_date
from .errors import NotFound
from .model import STATUSES


def add_filter_args(parser):
    parser.add_argument("--status", choices=STATUSES, help="only tasks with this status")
    parser.add_argument("--project", help="only tasks in this project")
    parser.add_argument("--tag", help="only tasks with this tag")
    parser.add_argument("--due-before", metavar="DATE", help="only tasks due before this date")


def select(store, args):
    """The tasks matching the filter arguments, in id order."""
    if args.project is not None and args.project not in store.projects():
        raise NotFound(f"no project {args.project!r}")
    cutoff = parse_date(args.due_before, "--due-before") if args.due_before is not None else None
    found = []
    for task in sorted(store.tasks, key=lambda t: t.id):
        if args.status and task.status != args.status:
            continue
        if args.project and task.project != args.project:
            continue
        if args.tag and args.tag not in task.tags:
            continue
        if cutoff is not None and (task.due is None or parse_date(task.due, "due") >= cutoff):
            continue
        found.append(task)
    return found

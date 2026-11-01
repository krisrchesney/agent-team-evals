from ..filters import add_filter_args, select
from ..model import STATUSES

NAME = "stats"
HELP = "count tasks by status and project"


def configure(parser):
    add_filter_args(parser)
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def run(args, con, store, clock):
    tasks = select(store, args)
    by_status = {status: sum(1 for t in tasks if t.status == status) for status in STATUSES}
    by_project = {}
    for task in tasks:
        by_project[task.project] = by_project.get(task.project, 0) + 1
    con.say(f"{len(tasks)} tasks")
    for status, n in by_status.items():
        con.say(f"  {status}: {n}")
    for project in sorted(by_project):
        con.say(f"  {project}: {by_project[project]}")
    con.emit({"command": NAME, "total": len(tasks), "by_status": by_status, "by_project": by_project})
    if not tasks:
        con.warn("no tasks match")

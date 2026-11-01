from ..views import task_detail

NAME = "show"
HELP = "show one task"


def configure(parser):
    parser.add_argument("id", type=int)
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def run(args, con, store, clock):
    task = store.get(args.id)
    con.say(task_detail(task))
    con.emit({"command": NAME, "item": task.to_dict()})

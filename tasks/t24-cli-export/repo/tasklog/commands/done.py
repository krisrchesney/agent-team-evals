from ..errors import Conflict

NAME = "done"
HELP = "mark a task done"


def configure(parser):
    parser.add_argument("id", type=int)
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def run(args, con, store, clock):
    task = store.get(args.id)
    if task.status == "done":
        raise Conflict(f"task #{task.id} is already done")
    task.status = "done"
    store.save()
    con.say(f"task #{task.id} is done")
    con.emit({"command": NAME, "item": task.to_dict()})

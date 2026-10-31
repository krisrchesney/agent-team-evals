import json
import os

from .. import atomicio
from ..errors import Conflict, IoFailure

NAME = "backup"
HELP = "write a copy of the whole store to a file"


def configure(parser):
    parser.add_argument("path")
    parser.add_argument("--force", action="store_true", help="replace the file if it exists")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def run(args, con, store, clock):
    if os.path.exists(args.path) and not args.force:
        raise Conflict(f"{args.path} already exists (use --force)")
    text = json.dumps(store.document(), indent=2, ensure_ascii=False) + "\n"
    try:
        atomicio.write_text(args.path, text)
    except OSError as err:
        raise IoFailure(f"cannot write {args.path}: {err.strerror or err}") from None
    con.say(f"backed up {len(store.tasks)} tasks to {args.path}")
    con.emit({"command": NAME, "count": len(store.tasks), "output": args.path})
    if not store.tasks:
        con.warn("no tasks to back up")

import argparse
import os
import sys

from . import exitcodes
from .clock import SystemClock
from .commands import COMMANDS
from .console import Console
from .errors import CliError, UsageError
from .store import Store


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def build_parser():
    parser = Parser(prog="tasklog", description="A small task list for the terminal.")
    parser.add_argument("--store", default=os.environ.get("TASKLOG_STORE", "tasks.json"),
                        help="the task file (default: tasks.json, or $TASKLOG_STORE)")
    parser.add_argument("-q", "--quiet", action="store_true", help="print no normal output")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    for module in COMMANDS:
        child = sub.add_parser(module.NAME, help=module.HELP)
        module.configure(child)
        child.set_defaults(handler=module.run)
    return parser


def main(argv=None, stdout=None, stderr=None, clock=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    con = Console(stdout or sys.stdout, stderr or sys.stderr, as_json="--json" in argv)
    try:
        args = build_parser().parse_args(argv)
        con.command = args.command
        con.quiet = args.quiet
        con.as_json = getattr(args, "json", False)
        store = Store.load(args.store)
        args.handler(args, con, store, clock or SystemClock())
        return exitcodes.OK
    except CliError as err:
        con.error(err)
        return err.code

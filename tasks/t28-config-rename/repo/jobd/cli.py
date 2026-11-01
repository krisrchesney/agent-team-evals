"""Command line: `python -m jobd.cli [--config FILE] [--worker-threads N ...] COMMAND`."""
import argparse
import sys
import warnings

from .admin import config_show, doctor, status
from .config import DeprecatedSettingWarning, loader
from .config.cli_flags import add_flags
from .errors import JobdError
from .queue import JobQueue
from .runtime.pool import WorkerPool


def build_parser():
    parser = argparse.ArgumentParser(prog="jobd")
    parser.add_argument("--config", help="path to a .json or .ini config file")
    add_flags(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show the pool and queue")
    sub.add_parser("doctor", help="check the configuration")
    show = sub.add_parser("config", help="show configuration")
    show.add_argument("what", choices=("show", "defaults", "describe"))
    return parser


def main(argv=None, out=None, err=None, environ=None):
    out, err = out or sys.stdout, err or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecatedSettingWarning)
            settings = loader.load(path=args.config, environ=environ, args=args)
        for w in caught:
            if issubclass(w.category, DeprecatedSettingWarning):
                print(f"warning: {w.message}", file=err)
    except JobdError as exc:
        print(f"error: {exc.message}", file=err)
        return 2
    if args.command == "status":
        out.write(status.format_status(settings, WorkerPool(settings), JobQueue(settings.queue_size)))
    elif args.command == "doctor":
        out.write(doctor.format_findings(doctor.check(settings)))
    elif args.what == "show":
        out.write(config_show.show(settings))
    elif args.what == "defaults":
        out.write(config_show.dump_defaults())
    else:
        out.write(config_show.describe())
    return 0


if __name__ == "__main__":
    sys.exit(main())

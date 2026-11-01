"""Command-line flags: one `--setting-name VALUE` per setting."""
import argparse

from .schema import SETTINGS


def flag_for(name):
    return "--" + name.replace("_", "-")


def add_flags(parser):
    group = parser.add_argument_group("settings")
    for setting in SETTINGS.values():
        group.add_argument(flag_for(setting.name), dest=setting.name, default=None, metavar=setting.kind.upper(),
                           help=setting.doc)
    # Removed from --help in 1.2 but still accepted: the old spelling of --log-level.
    group.add_argument("--loglevel", dest="loglevel", default=None, help=argparse.SUPPRESS)
    return parser


def read(namespace):
    """Raw values for every flag that was given, keyed by setting name (old names included)."""
    out = {}
    for name in list(SETTINGS) + ["loglevel"]:
        value = getattr(namespace, name, None)
        if value is not None:
            out[name] = value
    return out

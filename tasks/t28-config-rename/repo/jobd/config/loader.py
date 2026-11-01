"""Putting the layers together: defaults < config file < environment < command line."""
import os

from . import cli_flags, env, files, values
from .deprecations import apply_renames
from .schema import defaults
from .settings import Settings


def layers(path=None, environ=None, args=None):
    """[(source label, raw dict)] from lowest to highest priority."""
    out = []
    if path:
        out.append((f"file {path}", files.read(path)))
    out.append(("environment", env.read(os.environ if environ is None else environ)))
    if args is not None:
        out.append(("command line", cli_flags.read(args)))
    return out


def load(path=None, environ=None, args=None):
    merged = defaults()
    for source, raw in layers(path, environ, args):
        for name, value in apply_renames(raw, source).items():
            merged[name] = values.coerce(name, value, source)
    return Settings(merged)

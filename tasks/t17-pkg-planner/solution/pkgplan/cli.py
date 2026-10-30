"""Command line: show, list, rdeps and plan."""
import json
import sys

from .errors import ConstraintError, LockError, ResolutionError, VersionError
from .graph import reachable, reverse_dependencies
from .lockfile import dump_lock, load_lock
from .planner import build_plan
from .registry import Registry
from .report import format_report
from .resolver import resolve

_VALUE_OPTIONS = {"--registry", "--installed", "--upgrade", "--write-lock"}
_FLAG_OPTIONS = {"--upgrade-all", "--prerelease"}


class UsageError(Exception):
    pass


def _parse(args):
    options = {"--upgrade": []}
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _VALUE_OPTIONS:
            if i + 1 >= len(args):
                raise UsageError(f"{arg} needs a value")
            if arg == "--upgrade":
                options[arg].append(args[i + 1])
            else:
                options[arg] = args[i + 1]
            i += 2
        elif arg in _FLAG_OPTIONS:
            options[arg] = True
            i += 1
        elif arg.startswith("--"):
            raise UsageError(f"unknown option {arg}")
        else:
            positional.append(arg)
            i += 1
    return options, positional


def _read(path, what):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise UsageError(f"cannot read {what} {path}: {exc.strerror or exc}") from None


def _registry_path(options):
    if "--registry" not in options:
        raise UsageError("--registry FILE is required")
    return options["--registry"]


def _load_registry(path):
    try:
        return Registry.from_dict(json.loads(_read(path, "registry")))
    except (ValueError, AttributeError, TypeError) as exc:
        if isinstance(exc, (VersionError, ConstraintError)):
            raise
        raise UsageError(f"bad registry {path}: {exc}") from None


def _one_name(positional, command):
    if len(positional) != 1:
        raise UsageError(f"{command} takes exactly one package name")
    return positional[0]


def _show(options, positional, out):
    name = _one_name(positional, "show")
    registry = _load_registry(_registry_path(options))
    if name not in registry:
        raise ResolutionError(f"unknown package {name}")
    out.write(registry.display_name(name) + "\n")
    for pv in registry.versions(name):
        out.write(f"  {pv.version}{' (yanked)' if pv.yanked else ''}\n")


def _list(options, positional, out):
    if positional:
        raise UsageError("list takes no arguments")
    registry = _load_registry(_registry_path(options))
    for name in registry.names():
        out.write(f"{name} {len(registry.versions(name))}\n")


def _rdeps(options, positional, out):
    name = _one_name(positional, "rdeps")
    registry = _load_registry(_registry_path(options))
    if name not in registry:
        raise ResolutionError(f"unknown package {name}")
    for dependent in reverse_dependencies(registry, name):
        out.write(dependent + "\n")


def _reach(options, positional, out):
    name = _one_name(positional, "reach")
    registry = _load_registry(_registry_path(options))
    if name not in registry:
        raise ResolutionError(f"unknown package {name}")
    for dependency in reachable(registry, name):
        out.write(dependency + "\n")


def _plan(options, positional, out):
    if not positional:
        raise UsageError("no requirements given")
    registry = _load_registry(_registry_path(options))
    installed = load_lock(_read(options["--installed"], "lock file")) if "--installed" in options else {}
    resolved = resolve(registry, positional, installed=installed, upgrade=options["--upgrade"],
                       upgrade_all=options.get("--upgrade-all", False),
                       prerelease=options.get("--prerelease", False))
    steps = build_plan(resolved, installed)
    out.write(format_report(steps))
    if "--write-lock" in options:
        try:
            with open(options["--write-lock"], "w", encoding="utf-8", newline="\n") as handle:
                handle.write(dump_lock(steps))
        except OSError as exc:
            raise UsageError(f"cannot write lock file: {exc.strerror or exc}") from None


_COMMANDS = {"show": _show, "list": _list, "rdeps": _rdeps, "reach": _reach, "plan": _plan}


def main(argv, out=None, err=None):
    """Run the CLI. Returns 0 on success, 2 for a resolution problem, 64 for bad input."""
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr
    try:
        if not argv or argv[0] not in _COMMANDS:
            raise UsageError("usage: pkgplan (" + "|".join(_COMMANDS) + ") --registry FILE ...")
        options, positional = _parse(list(argv[1:]))
        _COMMANDS[argv[0]](options, positional, out)
        return 0
    except ResolutionError as exc:
        err.write(f"error: {exc}\n")
        return 2
    except (UsageError, VersionError, ConstraintError, LockError) as exc:
        err.write(f"error: {exc}\n")
        return 64

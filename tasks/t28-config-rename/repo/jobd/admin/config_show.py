"""`jobd config show` and `jobd config defaults`."""
import json

from ..config.schema import SETTINGS, defaults


def show(settings):
    """One `name = value` line per setting, with a `(default)` mark where nothing was changed."""
    width = max(len(name) for name in SETTINGS)
    base = defaults()
    lines = []
    for name, setting in SETTINGS.items():
        value = settings.as_dict()[name]
        mark = "  (default)" if value == base[name] else ""
        lines.append(f"{name:<{width}} = {value}{mark}")
    return "\n".join(lines) + "\n"


def dump_defaults():
    """The default configuration as the JSON a config file would contain."""
    return json.dumps(defaults(), indent=2) + "\n"


def describe():
    """Every setting with its description, for `--help`-style output."""
    width = max(len(name) for name in SETTINGS)
    return "\n".join(f"{s.name:<{width}}  {s.doc}" for s in SETTINGS.values()) + "\n"

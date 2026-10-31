import json

from .errors import FlagConfigError


def load_specs(text):
    """Read flag definitions from JSON text: a list of dicts, or {"flags": [...]}."""
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("flags")
    if not isinstance(data, list):
        raise FlagConfigError("?", "flags", "expected a list of flag definitions")
    return data


def load_file(path):
    with open(path, encoding="utf-8") as fh:
        return load_specs(fh.read())

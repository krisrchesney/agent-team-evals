"""Load application settings from an INI file over built-in defaults."""
import configparser
import copy

DEFAULTS = {
    "server": {"host": "127.0.0.1", "port": 8000, "debug": False},
    "database": {"url": "sqlite:///app.db", "pool_size": 5, "timeout": 30.0},
}


class ConfigError(ValueError):
    """A setting has a value that cannot be used."""


def _coerce(default, raw):
    if isinstance(default, str):
        return raw
    return type(default)(raw.strip())


def load(path):
    settings = copy.deepcopy(DEFAULTS)
    parser = configparser.ConfigParser(interpolation=None)
    with open(path, encoding="utf-8") as fh:
        parser.read_file(fh)
    for section in parser.sections():
        values = settings.setdefault(section, {})
        known = DEFAULTS.get(section, {})
        for key, raw in parser.items(section):
            if key in known:
                try:
                    values[key] = _coerce(known[key], raw)
                except ValueError:
                    raise ConfigError(f"bad value {raw!r}") from None
            else:
                values[key] = raw
    return settings

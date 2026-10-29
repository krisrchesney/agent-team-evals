"""Load application settings from an INI file over built-in defaults, with env overrides."""
import configparser
import copy
import os

DEFAULTS = {
    "server": {"host": "127.0.0.1", "port": 8000, "debug": False},
    "database": {"url": "sqlite:///app.db", "pool_size": 5, "timeout": 30.0},
}

PREFIX = "APP_"
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


class ConfigError(ValueError):
    """A setting has a value that cannot be used."""


def _coerce(default, raw):
    if isinstance(default, str):
        return raw
    if isinstance(default, bool):
        word = raw.strip().lower()
        if word in _TRUE:
            return True
        if word in _FALSE:
            return False
        raise ValueError(f"not a boolean: {raw!r}")
    return type(default)(raw.strip())


def _convert(default, raw, source):
    try:
        return _coerce(default, raw)
    except ValueError:
        raise ConfigError(f"{source}: bad value {raw!r}") from None


def load(path=None, env=None):
    if env is None:
        env = os.environ
    settings = copy.deepcopy(DEFAULTS)
    if path is not None:
        parser = configparser.ConfigParser(interpolation=None)
        with open(path, encoding="utf-8") as fh:
            parser.read_file(fh)
        for section in parser.sections():
            values = settings.setdefault(section, {})
            known = DEFAULTS.get(section, {})
            for key, raw in parser.items(section):
                if key in known:
                    values[key] = _convert(known[key], raw, f"{section}.{key}")
                else:
                    values[key] = raw
    for section, known in DEFAULTS.items():
        for key, default in known.items():
            name = f"{PREFIX}{section.upper()}__{key.upper()}"
            raw = env.get(name)
            if raw is None or not raw.strip():
                continue  # empty or whitespace-only counts as not set
            settings[section][key] = _convert(default, raw, name)
    return settings

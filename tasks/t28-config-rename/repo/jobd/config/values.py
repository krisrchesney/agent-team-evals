"""Turning raw values (strings from env and flags, JSON values from files) into typed settings."""
from ..errors import ConfigError
from .schema import SETTINGS

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _fail(name, source, text):
    raise ConfigError(f"{name}: {text} (from {source})", field=name)


def coerce(name, raw, source):
    setting = SETTINGS.get(name)
    if setting is None:
        _fail(name, source, "unknown setting")
    kind = setting.kind
    try:
        if kind == "int":
            if isinstance(raw, bool) or (isinstance(raw, float) and raw != int(raw)):
                raise ValueError
            value = int(raw)
        elif kind == "float":
            if isinstance(raw, bool):
                raise ValueError
            value = float(raw)
        elif kind == "bool":
            value = _to_bool(raw)
        else:
            value = str(raw)
    except (TypeError, ValueError):
        _fail(name, source, f"{raw!r} is not a valid {kind}")
    if setting.minimum is not None and value < setting.minimum:
        _fail(name, source, f"must be at least {setting.minimum:g}")
    if setting.maximum is not None and value > setting.maximum:
        _fail(name, source, f"must be at most {setting.maximum:g}")
    if setting.choices is not None and value not in setting.choices:
        _fail(name, source, f"must be one of {', '.join(setting.choices)}")
    return value


def _to_bool(raw):
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ValueError(raw)

"""Filters keep or drop records. A spec is `name:arg`; FILTERS maps a name to a factory
that takes the arg and returns a predicate(record) -> bool."""
from .errors import ConfigError
from .record import LEVELS

FILTERS = {}


def register(name):
    def deco(factory):
        FILTERS[name] = factory
        return factory

    return deco


@register("level")
def level_filter(arg):
    wanted = arg.strip().upper()
    if wanted not in LEVELS:
        raise ConfigError(f"bad level '{arg}'")
    floor = LEVELS.index(wanted)
    return lambda rec: LEVELS.index(rec.level) >= floor


@register("contains")
def contains_filter(arg):
    return lambda rec: arg in rec.msg


@register("field")
def field_filter(arg):
    key, sep, value = arg.partition("=")
    if not sep:
        raise ConfigError(f"bad field filter '{arg}'")
    return lambda rec: key in rec.fields and rec.fields[key] == value


def _timestamp(arg):
    try:
        return int(arg)
    except ValueError:
        raise ConfigError(f"bad timestamp '{arg}'") from None


@register("since")
def since_filter(arg):
    start = _timestamp(arg)
    return lambda rec: rec.ts >= start


@register("until")
def until_filter(arg):
    end = _timestamp(arg)
    return lambda rec: rec.ts < end


@register("not")
def not_filter(arg):
    inner = build_filter(arg)
    return lambda rec: not inner(rec)


def build_filter(spec):
    name, _, arg = spec.partition(":")
    factory = FILTERS.get(name)
    if factory is None:
        raise ConfigError(f"unknown filter '{name}'")
    return factory(arg)

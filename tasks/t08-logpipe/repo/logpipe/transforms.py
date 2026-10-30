"""Transforms rewrite a record. A spec is `name:arg`; TRANSFORMS maps a name to a function
(record, arg) -> record."""
import dataclasses

from .errors import ConfigError

TRANSFORMS = {}


def register(name):
    def deco(fn):
        TRANSFORMS[name] = fn
        return fn

    return deco


@register("upper")
def upper(rec, arg):
    return dataclasses.replace(rec, msg=rec.msg.upper())


@register("truncate")
def truncate(rec, arg):
    try:
        n = int(arg)
    except ValueError:
        raise ConfigError(f"bad truncate length '{arg}'") from None
    return dataclasses.replace(rec, msg=rec.msg[:n])


@register("redact")
def redact(rec, arg):
    return dataclasses.replace(rec, msg=rec.msg.replace(arg, "***"))


def build_transform(spec):
    name, _, arg = spec.partition(":")
    fn = TRANSFORMS.get(name)
    if fn is None:
        raise ConfigError(f"unknown transform '{name}'")
    return lambda rec: fn(rec, arg)

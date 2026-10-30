"""Transforms rewrite a record. A spec is `name:arg`; TRANSFORMS maps a name to a factory
that takes the arg and returns a step(record) -> record or None (None drops the record).
The factory runs once per pipeline run, so a step may keep state."""
import dataclasses

from .errors import ConfigError

TRANSFORMS = {}


def register(name):
    def deco(factory):
        TRANSFORMS[name] = factory
        return factory

    return deco


@register("upper")
def upper(arg):
    return lambda rec: dataclasses.replace(rec, msg=rec.msg.upper())


@register("truncate")
def truncate(arg):
    try:
        n = int(arg)
    except ValueError:
        raise ConfigError(f"bad truncate length '{arg}'") from None
    return lambda rec: dataclasses.replace(rec, msg=rec.msg[:n])


@register("redact")
def redact(arg):
    return lambda rec: dataclasses.replace(rec, msg=rec.msg.replace(arg, "***"))


@register("dedupe")
def dedupe(arg):
    try:
        window = int(arg)
    except ValueError:
        window = 0
    if window < 1:
        raise ConfigError(f"bad dedupe window '{arg}'")
    last_kept = {}

    def step(rec):
        key = (rec.level, rec.msg)
        if key in last_kept and rec.ts - last_kept[key] < window:
            return None
        last_kept[key] = rec.ts
        return rec

    return step


@register("rename")
def rename(arg):
    old, sep, new = arg.partition("=")
    if not (sep and old and new):
        raise ConfigError(f"bad rename '{arg}'")

    def step(rec):
        if old not in rec.fields or old == new:
            return rec
        fields = {}
        for key, value in rec.fields.items():
            if key == old:
                fields[new] = value
            elif key != new:
                fields[key] = value
        return dataclasses.replace(rec, fields=fields)

    return step


def build_transform(spec):
    name, _, arg = spec.partition(":")
    factory = TRANSFORMS.get(name)
    if factory is None:
        raise ConfigError(f"unknown transform '{name}'")
    return factory(arg)

"""The registry of output formats. A renderer is a callable `renderer(columns, rows) -> str`."""
from . import renderers


class UnknownFormatError(ValueError):
    pass


_registry = {}


def register(name, renderer, replace=False):
    if not isinstance(name, str) or not name:
        raise ValueError("format name must be a non-empty string")
    if not callable(renderer):
        raise TypeError("renderer must be callable")
    if name in _registry and not replace:
        raise ValueError("format %r is already registered" % (name,))
    _registry[name] = renderer


def unregister(name):
    del _registry[name]


def get(name):
    try:
        return _registry[name]
    except (KeyError, TypeError):
        raise UnknownFormatError("unknown format %r" % (name,)) from None


def names():
    return sorted(_registry)


register("csv", renderers.render_csv)
register("json", renderers.render_json)
register("table", renderers.render_table)

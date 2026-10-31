from . import plugins  # noqa: F401  (registers the built-in stage types)
from .errors import ConfigError
from .pipeline import Pipeline
from .registry import PLUGINS


def build_stage(spec):
    """A stage from {"type": ..., "name": ..., <options>}. The name defaults to the type."""
    if not isinstance(spec, dict) or not isinstance(spec.get("type"), str):
        raise ConfigError("?", "a stage needs a 'type'")
    options = {k: v for k, v in spec.items() if k not in ("type", "name")}
    name = spec.get("name", spec["type"])
    if not isinstance(name, str) or not name:
        raise ConfigError(str(name), "name must be a non-empty string")
    cls = PLUGINS.get(spec["type"])
    if cls is None:
        raise ConfigError(name, f"unknown stage type {spec['type']!r}")
    return cls(name, options)


def build_pipeline(specs):
    return Pipeline([build_stage(spec) for spec in specs])

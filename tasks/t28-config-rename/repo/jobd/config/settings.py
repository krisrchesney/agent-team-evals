"""The loaded configuration: typed values reachable as attributes."""
from . import deprecations
from .schema import SETTINGS, defaults


class Settings:
    def __init__(self, values=None):
        merged = defaults()
        merged.update(values or {})
        self._values = merged

    def __getattr__(self, name):
        values = self.__dict__.get("_values", {})
        if name in values:
            return values[name]
        raise AttributeError(name)

    @property
    def loglevel(self):
        """Old name of `log_level`."""
        deprecations.warn("loglevel", "log_level", stacklevel=3)
        return self._values["log_level"]

    def as_dict(self):
        return {name: self._values[name] for name in SETTINGS}

    def replace(self, **changes):
        new = dict(self._values)
        new.update(changes)
        return Settings(new)

    def __eq__(self, other):
        return isinstance(other, Settings) and self._values == other._values

    def __repr__(self):
        return f"Settings({self.as_dict()!r})"

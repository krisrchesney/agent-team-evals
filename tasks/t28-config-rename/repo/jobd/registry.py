"""Job handlers by name."""
from .errors import Conflict, NotFound


class HandlerRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, name, fn):
        if name in self._handlers:
            raise Conflict(f"handler {name!r} is already registered", field="handler")
        self._handlers[name] = fn
        return fn

    def handler(self, name):
        """Decorator form of `register`."""
        def wrap(fn):
            return self.register(name, fn)
        return wrap

    def get(self, name):
        try:
            return self._handlers[name]
        except KeyError:
            raise NotFound(f"no handler {name!r}", field="handler") from None

    def names(self):
        return sorted(self._handlers)

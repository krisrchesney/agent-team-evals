from ..errors import ConfigError
from ..registry import register
from ..stage import Stage


@register("dedupe")
class Dedupe(Stage):
    """Keep the first record for each key and drop the repeats."""
    OPTIONS = ("key",)
    REQUIRED = ("key",)

    def configure(self, options):
        key = options["key"]
        if not isinstance(key, list) or not key or not all(isinstance(f, str) and f for f in key):
            raise ConfigError(self.name, "key must be a non-empty list of field names")
        self.key = key
        self.seen = set()

    def open(self, context):
        self.seen = set()  # every run starts fresh

    def process(self, record):
        values = tuple(self.need(record, field) for field in self.key)
        try:
            hash(values)
        except TypeError:
            self.reject(record, f"key {list(self.key)} cannot be used as a key")
        if values in self.seen:
            return []
        self.seen.add(values)
        return [dict(record)]

    def close(self):
        self.seen = set()

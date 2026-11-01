from ..errors import ConfigError
from ..registry import register
from ..stage import Stage


@register("batch")
class Batch(Stage):
    """Group records into batches of `size`. A last, smaller batch goes out when the input ends."""
    OPTIONS = ("size",)
    REQUIRED = ("size",)

    def configure(self, options):
        size = options["size"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ConfigError(self.name, "size must be a whole number of at least 1")
        self.size = size
        self.pending = []

    def open(self, context):
        self.pending = []

    def _take(self):
        batch, self.pending = self.pending, []
        return {"batch": batch, "size": len(batch)}

    def process(self, record):
        self.pending.append(dict(record))
        return [self._take()] if len(self.pending) >= self.size else []

    def flush(self):
        return [self._take()] if self.pending else []

    def close(self):
        self.pending = []

from ..errors import ConfigError
from ..registry import register
from ..stage import Stage

OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "in": lambda a, b: a in b,
}
NUMERIC = ("gt", "gte", "lt", "lte")


@register("filter")
class Filter(Stage):
    """Keep the records whose field passes the test. Dropped records are not rejects."""
    OPTIONS = ("field", "op", "value")
    REQUIRED = ("field", "op", "value")

    def configure(self, options):
        self.field = options["field"]
        self.op = options["op"]
        self.value = options["value"]
        if not isinstance(self.field, str) or not self.field:
            raise ConfigError(self.name, "field must be a non-empty string")
        if self.op not in OPS:
            raise ConfigError(self.name, f"op must be one of {', '.join(OPS)}")
        if self.op == "in" and not isinstance(self.value, list):
            raise ConfigError(self.name, "value must be a list when op is 'in'")

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)  # True is not 1 here

    def process(self, record):
        value = self.need(record, self.field)
        if self.op in NUMERIC and not self._is_number(value):
            self.reject(record, f"{self.field!r} is not a number")
        return [dict(record)] if OPS[self.op](value, self.value) else []

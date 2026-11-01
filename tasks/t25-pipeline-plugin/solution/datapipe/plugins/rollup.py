from ..errors import ConfigError
from ..registry import register
from ..stage import Stage

AGGREGATES = ("count", "sum", "min", "max", "avg")


@register("rollup")
class Rollup(Stage):
    """One summary record per group of `by` values, emitted when the input ends."""
    OPTIONS = ("by", "field", "aggregates")
    REQUIRED = ("by",)

    def configure(self, options):
        by = options["by"]
        if not isinstance(by, list) or not by or not all(isinstance(f, str) and f for f in by):
            raise ConfigError(self.name, "by must be a non-empty list of field names")
        aggregates = options.get("aggregates", ["count"])
        if not isinstance(aggregates, list) or not aggregates:
            raise ConfigError(self.name, "aggregates must be a non-empty list")
        for agg in aggregates:
            if agg not in AGGREGATES:
                raise ConfigError(self.name, f"aggregate must be one of {', '.join(AGGREGATES)}, not {agg!r}")
        if len(set(aggregates)) != len(aggregates):
            raise ConfigError(self.name, "aggregates must not repeat")
        field = options.get("field")
        if aggregates != ["count"] and (not isinstance(field, str) or not field):
            raise ConfigError(self.name, "field is required unless count is the only aggregate")
        if field is not None and (not isinstance(field, str) or not field):
            raise ConfigError(self.name, "field must be a non-empty string")
        self.by, self.field, self.aggregates = by, field, aggregates
        self.groups = {}

    def open(self, context):
        self.groups = {}

    def process(self, record):
        key = tuple(self.need(record, f) for f in self.by)
        try:
            hash(key)
        except TypeError:
            self.reject(record, f"{self.by} cannot be used as a key")
        value = None
        if self.aggregates != ["count"]:
            value = self.need(record, self.field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                self.reject(record, f"{self.field!r} is not a number")
        group = self.groups.setdefault(key, {"count": 0, "values": []})
        group["count"] += 1
        if self.aggregates != ["count"]:
            group["values"].append(value)
        return []

    def _summary(self, key, group):
        out = dict(zip(self.by, key))
        values = group["values"]
        for agg in self.aggregates:
            if agg == "count":
                out["count"] = group["count"]
            elif agg == "sum":
                out[f"sum_{self.field}"] = sum(values)
            elif agg == "min":
                out[f"min_{self.field}"] = min(values)
            elif agg == "max":
                out[f"max_{self.field}"] = max(values)
            else:
                out[f"avg_{self.field}"] = sum(values) / len(values)
        return out

    def flush(self):
        out = [self._summary(key, group) for key, group in self.groups.items()]
        self.groups = {}
        return out

    def close(self):
        self.groups = {}

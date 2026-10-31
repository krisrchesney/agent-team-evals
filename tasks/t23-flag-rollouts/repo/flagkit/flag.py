from .errors import FlagConfigError

FLAG_TYPES = {}


def flag_type(name):
    def register(cls):
        if name in FLAG_TYPES:
            raise ValueError(f"flag type {name!r} registered twice")
        cls.type = name
        FLAG_TYPES[name] = cls
        return cls
    return register


class Flag:
    """Base of every flag type. Subclasses implement evaluate, from_spec and type_fields."""
    type = None

    def __init__(self, key, enabled=True, salt=None, overrides=None):
        self.key = key
        self.enabled = enabled
        self.salt = salt or key
        self.overrides = dict(overrides or {})

    @staticmethod
    def from_dict(spec):
        if not isinstance(spec, dict):
            raise FlagConfigError("?", "spec", "a flag definition must be a dict")
        key = spec.get("key")
        if not isinstance(key, str) or not key.strip():
            raise FlagConfigError(str(key), "key", "must be a non-empty string")
        key = key.strip()
        kind = spec.get("type")
        cls = FLAG_TYPES.get(kind)
        if cls is None:
            raise FlagConfigError(key, "type", f"unknown flag type {kind!r}")
        enabled = spec.get("enabled", True)
        if not isinstance(enabled, bool):
            raise FlagConfigError(key, "enabled", "must be true or false")
        salt = spec.get("salt")
        if salt is not None and (not isinstance(salt, str) or not salt):
            raise FlagConfigError(key, "salt", "must be a non-empty string")
        raw = spec.get("overrides") or {}
        if not isinstance(raw, dict):
            raise FlagConfigError(key, "overrides", "must map user ids to true or false")
        overrides = {}
        for user, value in raw.items():
            if not isinstance(value, bool):
                raise FlagConfigError(key, f"overrides.{user}", "must be true or false")
            overrides[str(user).strip()] = value
        common = {"key": key, "enabled": enabled, "salt": salt, "overrides": overrides}
        return cls.from_spec(common, spec)

    @classmethod
    def from_spec(cls, common, spec):
        raise NotImplementedError

    def type_fields(self):
        raise NotImplementedError

    def evaluate(self, ctx, now):
        raise NotImplementedError

    def to_dict(self):
        out = {"key": self.key, "type": self.type, "enabled": self.enabled,
               "salt": self.salt, "overrides": dict(self.overrides)}
        out.update(self.type_fields())
        return out

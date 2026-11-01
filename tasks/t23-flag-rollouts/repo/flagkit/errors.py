class FlagError(Exception):
    pass


class FlagConfigError(FlagError):
    """A flag definition is wrong. `flag` is its key, `field` the part of the definition at fault."""

    def __init__(self, flag, field, message):
        super().__init__(f"flag {flag!r}: {field}: {message}")
        self.flag = flag
        self.field = field
        self.message = message


class UnknownFlag(FlagError):
    def __init__(self, key):
        super().__init__(f"no flag {key!r}")
        self.key = key

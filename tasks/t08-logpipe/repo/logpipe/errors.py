"""Errors the command line reports as `logpipe: error: ...`."""


class ParseError(ValueError):
    """A log line is malformed."""


class ConfigError(ValueError):
    """A filter, transform or format spec is wrong."""

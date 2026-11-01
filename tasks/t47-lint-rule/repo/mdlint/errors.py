class LintError(Exception):
    pass


class ConfigError(LintError):
    """A rule is set up wrongly. Raised while the linter is built, never while it runs."""

    def __init__(self, rule, message):
        super().__init__(f"rule {rule!r}: {message}")
        self.rule = rule
        self.message = message


class RuleError(LintError):
    """A rule crashed. `line` is the line it was checking, or None if it crashed at the end."""

    def __init__(self, rule, line, cause):
        where = "at the end of the document" if line is None else f"on line {line}"
        super().__init__(f"rule {rule!r} failed {where}: {cause}")
        self.rule = rule
        self.line = line
        self.cause = cause

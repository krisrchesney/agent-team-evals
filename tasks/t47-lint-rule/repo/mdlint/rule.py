from .errors import ConfigError
from .report import SEVERITIES, Violation


class Rule:
    """Base class of every rule.

    For each document the linter calls begin(doc) once, check(line) for every line, finish(doc) at the
    end, and then moves on. Rules keep what they learn while reading a document in `self.state`;
    begin() gives them a new one from fresh(), so a rule never carries anything from one document into
    the next. Rules implement what they need and leave the rest alone; report() and the linter take
    care of severity, naming and ordering.
    """
    OPTIONS = ()        # option names the rule understands
    REQUIRED = ()       # the ones that must be given
    PROSE_ONLY = False  # True: lines of fenced code blocks are not passed to check()

    def __init__(self, name, options):
        unknown = sorted(set(options) - set(self.OPTIONS) - {"severity"})
        if unknown:
            raise ConfigError(name, f"unknown option(s): {', '.join(unknown)}")
        missing = [opt for opt in self.REQUIRED if opt not in options]
        if missing:
            raise ConfigError(name, f"missing option(s): {', '.join(missing)}")
        self.name = name
        self.severity = options.get("severity", "error")
        if self.severity not in SEVERITIES:
            raise ConfigError(name, f"severity must be one of {', '.join(SEVERITIES)}")
        self.state = None
        self.found = []
        self.configure(options)

    # hooks for rules
    def configure(self, options):
        pass

    def fresh(self):
        """The state for one document."""
        return {}

    def check(self, line):
        pass

    def finish(self, doc):
        pass

    # helpers for rules
    def report(self, number, message):
        self.found.append(Violation(self.name, number, self.severity, message))

    # called by the linter
    def begin(self, doc):
        self.state = self.fresh()
        self.found = []

    def feed(self, line):
        if self.PROSE_ONLY and line.in_code:
            return
        self.check(line)

    def drain(self):
        found, self.found = self.found, []
        return found

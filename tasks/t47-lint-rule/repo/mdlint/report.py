from dataclasses import dataclass, field

SEVERITIES = ("error", "warning")


@dataclass(frozen=True)
class Violation:
    rule: str       # the rule's name
    line: int
    severity: str
    message: str

    def format(self, path):
        return f"{path}:{self.line}: {self.severity} {self.rule}: {self.message}"


@dataclass
class Report:
    path: str
    violations: list = field(default_factory=list)

    @property
    def ok(self):
        return not any(v.severity == "error" for v in self.violations)

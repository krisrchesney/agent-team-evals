from .document import Document
from .errors import ConfigError, RuleError
from .registry import RULES
from .report import Report


def build_rule(spec):
    """A rule from {"rule": ..., "name": ..., <options>}. The name defaults to the rule type."""
    if not isinstance(spec, dict) or not isinstance(spec.get("rule"), str):
        raise ConfigError("?", "a rule needs a 'rule' type")
    options = {k: v for k, v in spec.items() if k not in ("rule", "name")}
    name = spec.get("name", spec["rule"])
    if not isinstance(name, str) or not name:
        raise ConfigError(str(name), "name must be a non-empty string")
    cls = RULES.get(spec["rule"])
    if cls is None:
        raise ConfigError(name, f"unknown rule type {spec['rule']!r}")
    return cls(name, options)


class Linter:
    def __init__(self, rules):
        seen = set()
        for rule in rules:
            if rule.name in seen:
                raise ConfigError(rule.name, "two rules have this name")
            seen.add(rule.name)
        self.rules = list(rules)

    def lint(self, text, path="<text>"):
        doc = Document(text, path)
        violations = []
        for rule in self.rules:
            rule.begin(doc)
        for line in doc.lines:
            for rule in self.rules:
                try:
                    rule.feed(line)
                except Exception as err:
                    raise RuleError(rule.name, line.number, err) from err
                violations.extend(rule.drain())
        for rule in self.rules:
            try:
                rule.finish(doc)
            except Exception as err:
                raise RuleError(rule.name, None, err) from err
            violations.extend(rule.drain())
        return Report(path, violations)


def build_linter(specs):
    return Linter([build_rule(spec) for spec in specs])

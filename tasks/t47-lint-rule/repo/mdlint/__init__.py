"""mdlint: check Markdown documents against a list of rules.

    from mdlint import build_linter
    linter = build_linter([
        {"rule": "line-length", "max": 100},
        {"rule": "heading-increment", "severity": "warning"},
    ])
    report = linter.lint(text, path="README.md")
    report.violations, report.ok
"""
from . import rules  # noqa: F401  (registers the built-in rules)
from .errors import ConfigError, LintError, RuleError
from .linter import Linter, build_linter, build_rule

__all__ = ["build_linter", "build_rule", "Linter", "LintError", "ConfigError", "RuleError"]

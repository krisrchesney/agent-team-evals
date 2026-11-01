import unittest

from mdlint import ConfigError, RuleError, build_linter


class LintTest(unittest.TestCase):
    def test_line_length_and_trailing_space(self):
        linter = build_linter([{"rule": "line-length", "max": 10}, {"rule": "trailing-space"}])
        report = linter.lint("short\nthis line is long  \n")
        self.assertEqual([(v.rule, v.line) for v in report.violations],
                         [("line-length", 2), ("trailing-space", 2)])
        self.assertFalse(report.ok)

    def test_severity_and_names(self):
        linter = build_linter([{"rule": "trailing-space", "name": "ws", "severity": "warning"}])
        report = linter.lint("a \n")
        self.assertEqual([(v.rule, v.severity) for v in report.violations], [("ws", "warning")])
        self.assertTrue(report.ok)

    def test_heading_rules_skip_code(self):
        linter = build_linter([{"rule": "heading-increment"}, {"rule": "duplicate-heading"}])
        report = linter.lint("# A\n### B\n```\n# A\n#### C\n```\n# A\n")
        self.assertEqual([(v.rule, v.line) for v in report.violations],
                         [("heading-increment", 2), ("duplicate-heading", 7)])

    def test_each_document_starts_fresh(self):
        linter = build_linter([{"rule": "duplicate-heading"}, {"rule": "blank-lines"}])
        self.assertEqual(len(linter.lint("# A\n# A\n").violations), 1)
        self.assertEqual(len(linter.lint("# A\n").violations), 0)
        self.assertEqual(len(linter.lint("a\n\n\nb\n").violations), 1)
        self.assertEqual(len(linter.lint("\n").violations), 0)

    def test_final_newline(self):
        linter = build_linter([{"rule": "final-newline"}])
        self.assertEqual([v.line for v in linter.lint("a\nb").violations], [2])
        self.assertEqual(linter.lint("a\nb\n").violations, [])

    def test_config_errors(self):
        for spec in ({"rule": "nope"}, {"rule": "line-length"}, {"rule": "line-length", "max": 0},
                     {"rule": "trailing-space", "colour": "red"}, {"rule": "trailing-space", "severity": "fatal"}):
            with self.assertRaises(ConfigError):
                build_linter([spec])

    def test_a_crashing_rule_is_a_rule_error(self):
        linter = build_linter([{"rule": "trailing-space"}])
        linter.rules[0].check = lambda line: 1 / 0
        with self.assertRaises(RuleError):
            linter.lint("a\n")


if __name__ == "__main__":
    unittest.main()

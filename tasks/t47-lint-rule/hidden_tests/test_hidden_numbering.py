"""Hidden tests for t47-lint-rule. Every rule is shown by the starting code; see AUDIT.md."""
import unittest

from mdlint import ConfigError, build_linter, build_rule
from mdlint.registry import RULES
from mdlint.report import Violation


def numbering(**options):
    return dict({"rule": "list-numbering"}, **options)


def lint(text, *specs):
    return build_linter(list(specs) or [numbering()]).lint(text)


def found(text, *specs):
    return [(v.line, v.message) for v in lint(text, *specs).violations]


class TestRule(unittest.TestCase):
    def test_registered_and_named_after_its_type(self):
        self.assertIn("list-numbering", RULES)
        self.assertEqual(build_rule(numbering()).name, "list-numbering")
        self.assertEqual(build_rule(numbering(name="steps")).name, "steps")

    def test_a_correct_list_is_clean(self):
        self.assertEqual(found("1. a\n2. b\n3. c\n"), [])

    def test_wrong_numbers_are_reported_by_position(self):
        self.assertEqual(found("1. a\n3. b\n4. c\n"),
                         [(2, "expected 2, found 3"), (3, "expected 3, found 4")])

    def test_repeats_and_going_backwards(self):
        self.assertEqual(found("1. a\n1. b\n2. c\n"), [(2, "expected 2, found 1"), (3, "expected 3, found 2")])

    def test_the_violation_is_a_violation_of_the_rules_name(self):
        v = lint("1. a\n5. b\n").violations[0]
        self.assertEqual(v, Violation("list-numbering", 2, "error", "expected 2, found 5"))
        v = lint("5. a\n", numbering(name="steps")).violations[0]
        self.assertEqual((v.rule, v.line), ("steps", 1))

    def test_severity(self):
        report = lint("2. a\n", numbering(severity="warning"))
        self.assertEqual([v.severity for v in report.violations], ["warning"])
        self.assertTrue(report.ok)
        self.assertFalse(lint("2. a\n").ok)

    def test_a_list_must_start_at_one_by_default(self):
        self.assertEqual(found("2. a\n3. b\n"), [(1, "expected 1, found 2"), (2, "expected 2, found 3")])

    def test_start_option(self):
        self.assertEqual(found("0. a\n1. b\n", numbering(start=0)), [])
        self.assertEqual(found("5. a\n6. b\n7. c\n", numbering(start=5)), [])
        self.assertEqual(found("1. a\n", numbering(start=5)), [(1, "expected 5, found 1")])

    def test_a_number_beyond_any_int_size_does_not_crash(self):
        self.assertEqual(found("99999999999999999999. a\n"), [(1, "expected 1, found 99999999999999999999")])


class TestLists(unittest.TestCase):
    def test_blank_lines_do_not_end_a_list(self):
        self.assertEqual(found("1. a\n\n2. b\n\n\n3. c\n"), [])
        self.assertEqual(found("1. a\n\n3. b\n"), [(3, "expected 2, found 3")])

    def test_indented_lines_do_not_end_a_list(self):
        self.assertEqual(found("1. a\n   more of a\n2. b\n"), [])

    def test_indented_numbers_are_not_items(self):
        self.assertEqual(found("1. a\n   1. sub\n   2. sub\n2. b\n"), [])
        self.assertEqual(found("   5. just indented\n"), [])

    def test_other_lines_end_the_list(self):
        self.assertEqual(found("1. a\n2. b\ntext\n1. c\n2. d\n"), [])
        self.assertEqual(found("1. a\ntext\n2. b\n"), [(3, "expected 1, found 2")])

    def test_a_heading_ends_the_list(self):
        self.assertEqual(found("1. a\n# Next\n1. b\n"), [])

    def test_blank_lines_then_text_end_the_list(self):
        self.assertEqual(found("1. a\n\ntext\n\n1. b\n"), [])

    def test_each_list_is_counted_on_its_own(self):
        self.assertEqual(found("1. a\n3. b\ntext\n1. c\n3. d\n"),
                         [(2, "expected 2, found 3"), (5, "expected 2, found 3")])

    def test_only_a_dot_makes_an_item(self):
        self.assertEqual(found("1) a\n3) b\n"), [])

    def test_code_blocks_are_ignored(self):
        self.assertEqual(found("text\n```\n1. a\n5. b\n```\n"), [])
        self.assertEqual(found("```\n9. x\n```\n1. a\n2. b\n"), [])
        self.assertEqual(found("```text\n7. x\n```\n\n3. a\n"), [(5, "expected 1, found 3")])


class TestLifecycle(unittest.TestCase):
    def test_each_document_starts_fresh(self):
        linter = build_linter([numbering()])
        self.assertEqual(linter.lint("1. a\n2. b\n").violations, [])
        self.assertEqual(linter.lint("1. a\n2. b\n").violations, [])
        self.assertEqual(linter.lint("1. a\n2. b").violations, [])
        self.assertEqual([v.line for v in linter.lint("3. a\n").violations], [1])
        self.assertEqual(linter.lint("1. a\n").violations, [])

    def test_a_report_only_holds_its_own_violations(self):
        linter = build_linter([numbering()])
        first = linter.lint("2. a\n")
        second = linter.lint("2. a\n3. b\n")
        self.assertEqual(len(first.violations), 1)
        self.assertEqual(len(second.violations), 2)
        self.assertEqual(len(linter.lint("1. a\n").violations), 0)

    def test_violations_follow_the_order_of_the_rules_on_a_line(self):
        text = "1. a\n3. b  \n"
        a = lint(text, {"rule": "trailing-space"}, numbering())
        b = lint(text, numbering(), {"rule": "trailing-space"})
        self.assertEqual([v.rule for v in a.violations], ["trailing-space", "list-numbering"])
        self.assertEqual([v.rule for v in b.violations], ["list-numbering", "trailing-space"])

    def test_works_next_to_the_other_stateful_rules(self):
        linter = build_linter([numbering(), {"rule": "duplicate-heading"}, {"rule": "blank-lines"}])
        text = "# A\n1. a\n3. b\n# A\n"
        self.assertEqual([(v.rule, v.line) for v in linter.lint(text).violations],
                         [("list-numbering", 3), ("duplicate-heading", 4)])
        self.assertEqual([(v.rule, v.line) for v in linter.lint(text).violations],
                         [("list-numbering", 3), ("duplicate-heading", 4)])

    def test_two_instances_do_not_share_state(self):
        one, two = build_rule(numbering()), build_rule(numbering())
        linter = build_linter([])
        linter.rules = [one]
        linter.lint("1. a\n2. b\n")
        self.assertEqual(build_linter([numbering()]).lint("1. a\n").violations, [])
        linter.rules = [two]
        self.assertEqual(linter.lint("1. a\n").violations, [])


class TestConfig(unittest.TestCase):
    def test_bad_config_is_a_config_error_naming_the_rule(self):
        bad = [numbering(start=-1), numbering(start=True), numbering(start="1"), numbering(start=1.5),
               numbering(colour="red"), numbering(severity="fatal")]
        for spec in bad:
            with self.assertRaises(ConfigError) as ctx:
                build_linter([spec])
            self.assertEqual(ctx.exception.rule, "list-numbering")
        with self.assertRaises(ConfigError) as ctx:
            build_linter([numbering(name="steps", start=-3)])
        self.assertEqual(ctx.exception.rule, "steps")

    def test_valid_options_are_accepted(self):
        for spec in (numbering(), numbering(start=0), numbering(start=12), numbering(severity="warning")):
            build_linter([spec])

    def test_rule_names_must_be_unique(self):
        with self.assertRaises(ConfigError):
            build_linter([numbering(), numbering()])
        build_linter([numbering(), numbering(name="again", start=0)])


class TestExisting(unittest.TestCase):
    def test_other_rules_unchanged(self):
        linter = build_linter([{"rule": "heading-increment"}, {"rule": "final-newline"}])
        report = linter.lint("# A\n### B")
        self.assertEqual([(v.rule, v.line) for v in report.violations],
                         [("heading-increment", 2), ("final-newline", 2)])


if __name__ == "__main__":
    unittest.main()

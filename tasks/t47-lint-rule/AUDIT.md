# t47-lint-rule: where each hidden-test rule is shown

The repo has no docs folder. The prompt gives the list grammar, the numbering rule, `start` and the
message. Everything else is shown by the base class (`mdlint/rule.py`, `linter.py`) and the six existing
rules. This file is outside `repo/`, so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_registered_and_named_after_its_type` | `@register("list-numbering")` and import in `rules/__init__.py`; the name defaults to the type | `rules/__init__.py` comment; `linter.build_rule` |
| `test_a_correct_list_is_clean`, `test_wrong_numbers_...`, `test_repeats_...`, `test_a_list_must_start_at_one_by_default`, `test_start_option`, `test_a_number_beyond_...` | the numbering rule and message | prompt |
| `test_the_violation_is_a_violation_of_the_rules_name` | violations are made with `self.report(line, message)`: `Violation(self.name, line, self.severity, message)`, lines 1-based | `Rule.report`; every existing rule |
| `test_severity` | `severity` is handled by the base class, only if violations go through `report` | `Rule.__init__`, `Rule.report` |
| `test_blank_lines_...`, `test_indented_...`, `test_other_lines_end_the_list`, `test_a_heading_ends_the_list`, `test_blank_lines_then_text_...`, `test_each_list_is_counted_on_its_own`, `test_only_a_dot_makes_an_item` | the list grammar | prompt ("with no indent", "carries on over blank lines and indented lines, and ends at any other line") |
| `test_code_blocks_are_ignored` | prose rules set `PROSE_ONLY = True` so fenced lines never reach `check()`; a list in a fence is not a list | `Rule` (`PROSE_ONLY` comment); `heading_increment.py`, `duplicate_heading.py` |
| `test_each_document_starts_fresh`, `test_a_report_only_holds_its_own_violations`, `test_works_next_to_the_other_stateful_rules`, `test_two_instances_...` | per-document state lives in `self.state`, built by `fresh()`, which `begin()` calls for each document; state kept anywhere else (`configure`, `__init__`) leaks into the next document | `Rule` docstring; `heading_increment.py`, `duplicate_heading.py`, `blank_lines.py` (`fresh`); `tests/test_lint.py` `test_each_document_starts_fresh` |
| `test_violations_follow_the_order_of_the_rules_on_a_line` | free from the base class and the linter loop once `report` is used | `Linter.lint` |
| `test_bad_config_is_a_config_error_naming_the_rule` | options are validated in `configure()` with `ConfigError(self.name, message)`; unknown options and `severity` come from `Rule.__init__` (so `OPTIONS` must be set); whole numbers exclude bools; the custom name is used | `rule.py`; `line_length.py`, `blank_lines.py`; `linter.build_rule` |
| `test_valid_options_are_accepted`, `test_rule_names_must_be_unique` | the linter checks names; options are not over-validated | `linter.Linter` |
| `test_other_rules_unchanged` | regression | `tests/test_lint.py` |

Not tested on purpose: whether a code fence ends a list; leading zeros in numbers (`01.`); an item with
no text after the dot.

What makes it hard: the rule needs per-document state, and the natural place for it (`__init__` or
`configure`) leaks the count from one document into the next, which only shows when the same linter is
used twice. The prompt says so only in passing ("linting more than one document with the same linter").
Fenced code is skipped through a class flag, not through anything in the prompt. Both are visible in
`rule.py` and in the two heading rules.

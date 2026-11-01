# t36-patch-apply: where each hidden-test rule is shown

Every rule is written in `repo/docs/SPEC.md` (the prompt points to it). This file is outside `repo/`,
so agents never see it. Exact-output diff tests rely on the spec naming the algorithm
(`difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(context)`), so the output is
fully determined; the round-trip tests only need a correct diff.

| Test group | Rule | SPEC.md section |
|---|---|---|
| `TestMakeDiff` exact strings | header format, `@@` ranges (length 1 omitted, length 0 uses line before), body tags, `context`, grouping of nearby changes (gap <= 2 * context merges) | `make_diff` |
| `test_missing_final_newline_is_marked`, `test_marker_after_context_line` | `\ No newline at end of file` after the line, also after context lines; a line with and without newline differ | `make_diff`, intro |
| `test_carriage_returns_are_kept_in_lines` | split on `\n` only | intro, `lines.py` |
| `TestParse` structure, junk, multiple files | names cut at the tab, missing length = 1, junk ignored | `parse` |
| `test_body_is_read_by_counting` | a removed line `-- x` looks like `--- x`; counts decide where a hunk ends | `parse` |
| `test_empty_line_is_blank_context`, marker tests, header-only, extras, no trailing newline | the listed body-line rules | `parse` |
| `test_errors`, `test_error_line_numbers` | the listed `ParseError` cases; `.line` for a bad body line and a lone `---` | `parse` |
| `TestApplyFile` exact, offsets, nearest-first, forward on ties | candidate order `0, +1, -1, +2, -2, ...`, offset = position - nominal | `apply_file` 2, 3 |
| `test_later_hunks_start_from_the_previous_offset`, `test_hunks_cannot_match_before_the_previous_hunk` | `prev_offset` shifts the next hunk's start; `prev_end` bound | `apply_file` intro, 2, 4 |
| `test_failure_lists_every_failed_hunk_*` | all failures reported, later hunks still tried, nothing returned | `apply_file` 4 |
| fuzz tests | drops context from the ends only, up to `max_fuzz`; lower fuzz tried over all offsets first; nominal position counts dropped leading context; dropped lines stay as in the file | `apply_file` 1 to 3 |
| missing-newline and CR tests | line equality includes the newline | intro, `apply_file` |
| pure insertion tests | `old_len == 0` means insert after line `old_start`; empty pattern | `apply_file` 2 |
| `test_roundtrip_on_generated_texts` | diff, parse, apply (and reverse) agree, for context 0, 1, 3, with and without a final newline | all |
| `TestApplyPatchText` | create/delete/modify, new name used, strip, dry run, all-or-nothing, error order and attributes, unsafe paths, duplicates, reverse, files with CRLF and non-ASCII text, offsets and fuzz on files, patches with mail headers and a `-- ` signature | `apply_patch_text`, `parse` |
| `TestMakeTreeDiff` | sorted order, `/dev/null` names, empty-file headers, unchanged files skipped, round-trip through `apply_patch_text` | `make_tree_diff` |

What makes it hard: four dependent layers (diff, parse, one-file apply, tree apply) where each layer's
edge cases show up in the next one. The apply algorithm has several interacting rules (offset order,
fuzz outer loop, offset carried to the next hunk, the previous-hunk bound, nominal position with dropped
context, zero-length hunks). A solution that passes the happy path still fails many of the 60 tests.

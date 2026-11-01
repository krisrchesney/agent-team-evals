# patchkit spec

Text is handled as lines (see `lines.py`): split on `"\n"` only, each line keeps its `"\n"`, and only the
last line of a text may lack one. A `Line.text` in a hunk follows the same rule: a `text` with no `"\n"`
stands for "no newline at end of file". Two lines are equal only if their full text, newline included,
is equal.

## `make_diff(old, new, old_name="a", new_name="b", context=3)`

Returns the unified diff of two texts, or `""` if `old == new`.

- Header: `--- <old_name>\n+++ <new_name>\n` (no tabs, no timestamps).
- Hunks are the groups from `difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
  .get_grouped_opcodes(context)` (so nearby changes are in one hunk and `context` lines surround each
  change).
- Hunk header `@@ -<old range> +<new range> @@`. A range is `<start>,<length>`; when the length is 1 the
  `,<length>` is left out; when the length is 0 the start is the number of the line *before* the range
  (so `0` at the top of the file). Otherwise the start is the 1-based number of the first line.
- Each body line is its tag (`" "`, `-` or `+`) followed by the line text. A line whose text has no
  `"\n"` is followed by a new line `\ No newline at end of file`.
- The result always ends with `"\n"`.

## `parse(patch_text)`

Returns a list of `FilePatch`, one per file in the text, in order. `patch_text` is split on `"\n"`.

- Lines before the first file header, and lines between one file's last hunk and the next header, are
  ignored (`diff --git ...`, `index ...`, prose).
- A file header is a line starting `--- ` followed directly by a line starting `+++ `. The name is the rest
  of the line up to the first tab (a tab starts a timestamp that is dropped). Names are kept as written
  (`a/x.py`, `/dev/null`). Outside a hunk body, a `--- ` line that is not followed directly by a `+++ ` line is a
  `ParseError`.
- A hunk starts at a line matching `@@ -a[,b] +c[,d] @@` (anything after the second `@@` is ignored; a missing
  length is 1). The body is read by **counting**: exactly as many old-side lines (context and `-`) as `b`
  and new-side lines (context and `+`) as `d`. A hunk ends when both counts are used up, so a body line
  `--- x` (a removed line `-- x`) or `+++ x` is body text, not a header.
- Body lines: `" "`, `-`, `+` then the text; the line text gets `"\n"` appended. A line that is completely
  empty (a context line whose single space was stripped) is a context line with text `"\n"`. A line
  `\ No newline at end of file` (anything starting with a backslash) removes the `"\n"` from the text of
  the line before it and is not counted.
- `ParseError` (with `line` = 1-based line number in the patch text where it was noticed) for: a hunk body
  that reaches the end of the text before its counts are used up, a body line that starts with any other
  character (an `@@` line included), a body line that would take one side over its count while the other
  side is not finished, a `\` line that is the first line of a body, a malformed `@@` line, a hunk before
  any file header, and `--- ` without `+++ `. Lines after a hunk whose counts are used up are not part
  of it (they are ignored like any other text between hunks).
- A file patch may have no hunks (a header only), for example for an empty file.

## `apply_file(text, file_patch, max_fuzz=2)`

Applies a `FilePatch` to `text`. Returns `ApplyResult(text, hunks)` where `hunks` is a list of
`HunkResult(index, offset, fuzz)`, one per hunk in order (`index` is 1-based). With no hunks the text is
returned unchanged and `hunks` is empty.

Hunks are placed one after another in file order using the line numbers of the *original* file. For
each hunk, with `prev_end` (index just after the lines matched by the previous hunk, 0 for the first)
and `prev_offset` (the `offset` of the previous successfully placed hunk, 0 for the first):

1. For `fuzz` = 0, 1, ..., `max_fuzz`: drop `min(fuzz, c)` context lines from the start of the hunk and
   `min(fuzz, e)` from the end, where `c` and `e` are the numbers of context lines at the start and the
   end of the hunk body (when the hunk is only context, never drop more than the hunk has). The rest is
   the hunk's *pattern* (its context and `-` lines, in order, as texts) and its *replacement* (its
   context and `+` lines).
2. The nominal position is `old_start - 1` (`old_start` when `old_len == 0`) plus the number of
   leading context lines dropped. Candidate positions are `nominal + prev_offset + d` for
   d = 0, +1, -1, +2, -2, ... and a candidate counts only if it is `>= prev_end` and the pattern fits in the
   file from there. The first candidate where the file's lines equal the pattern wins. An empty pattern
   matches at the first valid candidate.
3. The first (fuzz, candidate) that matches places the hunk: its lines are replaced by the replacement
   (dropped context lines stay as the file has them), the result records `offset = position - nominal`
   and the `fuzz` used, `prev_end = position + len(pattern)` and `prev_offset = offset`.
   Lower fuzz is always tried over all candidates before the next fuzz level.
4. If nothing matches the hunk fails; `prev_end` and `prev_offset` do not change, and the next hunk is
   still tried.

If any hunk failed, raise `PatchFailed` with `failed` = the 1-based numbers of all failed hunks, in order,
and return nothing. A successful call changes nothing but the returned text.

## `apply_patch_text(patch_text, root, strip=1, max_fuzz=2, dry_run=False, reverse=False)`

Parses `patch_text` and applies it to the files under the directory `root`. Returns a list of
`FileResult(path, action, hunks)`, one per file patch in order: `path` is the stripped path with `/`
separators, `action` is `"create"`, `"delete"` or `"modify"`, `hunks` the `HunkResult` list.

- `reverse=True` first replaces every file patch by its `.reversed()`.
- A file patch with old name `/dev/null` is a create, one with new name `/dev/null` is a delete, else a
  modify. The path is the new name (the old name for a delete), with the first `strip` `/`-separated
  components removed. If that leaves no components, starts with `/`, or has a `..` component, raise
  `UnsafePath`. A name of `/dev/null` is never stripped.
- Create: the path must not exist (`FileExists`); the hunks are applied to the empty text. Parent
  directories are created. Modify and delete: the file must exist (`MissingFile`). A delete removes the
  file after its hunks applied cleanly.
- Two file patches with the same resulting path raise `DuplicateTarget`.
- Files are read and written as UTF-8 with no newline translation (a `"\r"` stays).
- Everything is worked out in memory first, in patch order; the first error is raised (a `PatchFailed`
  from a file gets that file's stripped path in `.path`), and then **nothing** has been written. With
  `dry_run=True` the results are returned and nothing is written either.

## `make_tree_diff(old_tree, new_tree, context=3)`

`old_tree` and `new_tree` map paths to texts. Returns one patch text for all differences, files in sorted
path order, joined as plain concatenation: a modified file is `make_diff(old, new, "a/<path>", "b/<path>")`,
a created file `make_diff("", new, "/dev/null", "b/<path>")`, a deleted file `make_diff(old, "", "a/<path>",
"/dev/null")`. Files whose text is equal are left out. A created or deleted file with empty text has no
hunks but still gets its two header lines. No differences gives `""`.
Applying the result with `strip=1` to a directory holding `old_tree` gives `new_tree`.

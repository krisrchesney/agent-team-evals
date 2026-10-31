"""Hidden tests for t36-patch-apply. Every rule is in docs/SPEC.md; see AUDIT.md."""
import os
import random
import tempfile
import unittest

from patchkit import (DuplicateTarget, FileExists, FilePatch, Hunk, Line, MissingFile, ParseError, PatchFailed,
                      UnsafePath, apply_file, apply_patch_text, make_diff, make_tree_diff, parse)


def lines(text):
    return text.splitlines(keepends=True)


def one(old, new, **kw):
    return parse(make_diff(old, new, **kw))[0]


class TestMakeDiff(unittest.TestCase):
    def test_identical_is_empty(self):
        self.assertEqual(make_diff("a\nb\n", "a\nb\n"), "")
        self.assertEqual(make_diff("", ""), "")
        self.assertEqual(make_diff("a", "a"), "")

    def test_simple_replace_with_header(self):
        self.assertEqual(make_diff("a\nb\nc\n", "a\nB\nc\n"), "--- a\n+++ b\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n")
        self.assertEqual(make_diff("x\n", "y\n", "old.txt", "new.txt"),
                         "--- old.txt\n+++ new.txt\n@@ -1 +1 @@\n-x\n+y\n")

    def test_creating_and_emptying(self):
        self.assertEqual(make_diff("", "x\n"), "--- a\n+++ b\n@@ -0,0 +1 @@\n+x\n")
        self.assertEqual(make_diff("x\ny\n", ""), "--- a\n+++ b\n@@ -1,2 +0,0 @@\n-x\n-y\n")

    def test_context_is_configurable(self):
        old, new = "a\nb\nc\nd\ne\n", "a\nb\nC\nd\ne\n"
        self.assertEqual(make_diff(old, new, context=0), "--- a\n+++ b\n@@ -3 +3 @@\n-c\n+C\n")
        self.assertEqual(make_diff(old, new, context=1), "--- a\n+++ b\n@@ -2,3 +2,3 @@\n b\n-c\n+C\n d\n")
        self.assertEqual(make_diff("a\nb\n", "a\nX\nb\n", context=0), "--- a\n+++ b\n@@ -1,0 +2 @@\n+X\n")

    def test_missing_final_newline_is_marked(self):
        self.assertEqual(make_diff("a\nb", "a\nc"),
                         "--- a\n+++ b\n@@ -1,2 +1,2 @@\n a\n-b\n\\ No newline at end of file\n"
                         "+c\n\\ No newline at end of file\n")
        self.assertEqual(make_diff("a", "a\n"), "--- a\n+++ b\n@@ -1 +1 @@\n-a\n\\ No newline at end of file\n+a\n")
        self.assertEqual(make_diff("a\n", "a\nb"),
                         "--- a\n+++ b\n@@ -1 +1,2 @@\n a\n+b\n\\ No newline at end of file\n")

    def test_marker_after_context_line(self):
        self.assertEqual(make_diff("a\nb", "A\nb"),
                         "--- a\n+++ b\n@@ -1,2 +1,2 @@\n-a\n+A\n b\n\\ No newline at end of file\n")

    def test_far_apart_changes_make_two_hunks(self):
        old = "".join("l%d\n" % i for i in range(1, 21))
        new = old.replace("l2\n", "L2\n").replace("l19\n", "L19\n")
        out = make_diff(old, new)
        heads = [ln for ln in out.splitlines() if ln.startswith("@@")]
        self.assertEqual(heads, ["@@ -1,5 +1,5 @@", "@@ -16,5 +16,5 @@"])

    def test_close_changes_share_a_hunk(self):
        old = "".join("l%d\n" % i for i in range(1, 21))
        near = old.replace("l2\n", "L2\n").replace("l8\n", "L8\n")  # 5 unchanged lines between
        far = old.replace("l2\n", "L2\n").replace("l10\n", "L10\n")  # 7 unchanged lines between
        self.assertEqual([ln for ln in make_diff(near, old).splitlines() if ln.startswith("@@")], ["@@ -1,11 +1,11 @@"])
        self.assertEqual(len([ln for ln in make_diff(far, old).splitlines() if ln.startswith("@@")]), 2)

    def test_carriage_returns_are_kept_in_lines(self):
        self.assertEqual(make_diff("a\r\nb\r\n", "a\r\nB\r\n"), "--- a\n+++ b\n@@ -1,2 +1,2 @@\n a\r\n-b\r\n+B\r\n")


class TestParse(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(parse(""), [])
        self.assertEqual(parse("just some prose\n"), [])

    def test_structure(self):
        fp = parse("--- a/x.py\t2026-01-01 10:00:00\n+++ b/x.py\t2026-01-02 11:00:00\n"
                   "@@ -3,2 +3,3 @@ def f():\n keep\n-old\n+new1\n+new2\n")[0]
        self.assertEqual((fp.old_name, fp.new_name), ("a/x.py", "b/x.py"))
        h = fp.hunks[0]
        self.assertEqual((h.old_start, h.old_len, h.new_start, h.new_len), (3, 2, 3, 3))
        self.assertEqual([(ln.tag, ln.text) for ln in h.lines],
                         [(" ", "keep\n"), ("-", "old\n"), ("+", "new1\n"), ("+", "new2\n")])

    def test_missing_length_means_one(self):
        h = parse("--- a\n+++ b\n@@ -4 +4 @@\n-x\n+y\n")[0].hunks[0]
        self.assertEqual((h.old_len, h.new_len), (1, 1))

    def test_multiple_files_with_junk(self):
        text = ("diff --git a/one b/one\nindex 123..456 100644\n--- a/one\n+++ b/one\n@@ -1 +1 @@\n-a\n+b\n"
                "some prose between files\ndiff --git a/two b/two\n--- a/two\n+++ b/two\n@@ -1 +1 @@\n-c\n+d\n"
                "@@ -9 +9 @@\n-e\n+f\n")
        fps = parse(text)
        self.assertEqual([fp.new_name for fp in fps], ["b/one", "b/two"])
        self.assertEqual([len(fp.hunks) for fp in fps], [1, 2])

    def test_body_is_read_by_counting(self):
        text = "--- a\n+++ b\n@@ -1,2 +1,2 @@\n--- x\n-y\n+++ z\n+w\n--- a2\n+++ b2\n@@ -1 +1 @@\n-p\n+q\n"
        fps = parse(text)
        self.assertEqual(len(fps), 2)
        self.assertEqual([(ln.tag, ln.text) for ln in fps[0].hunks[0].lines],
                         [("-", "-- x\n"), ("-", "y\n"), ("+", "++ z\n"), ("+", "w\n")])

    def test_empty_line_is_blank_context(self):
        h = parse("--- a\n+++ b\n@@ -1,3 +1,3 @@\n a\n\n-b\n+c\n")[0].hunks[0]
        self.assertEqual([(ln.tag, ln.text) for ln in h.lines], [(" ", "a\n"), (" ", "\n"), ("-", "b\n"), ("+", "c\n")])

    def test_no_newline_marker(self):
        h = parse("--- a\n+++ b\n@@ -1,2 +1,2 @@\n a\n-b\n\\ No newline at end of file\n+c\n"
                  "\\ No newline at end of file\n")[0].hunks[0]
        self.assertEqual([(ln.tag, ln.text) for ln in h.lines], [(" ", "a\n"), ("-", "b"), ("+", "c")])

    def test_marker_after_context_line_and_mid_hunk(self):
        h = parse("--- a\n+++ b\n@@ -1,2 +1,2 @@\n-a\n+A\n b\n\\ No newline at end of file\n")[0].hunks[0]
        self.assertEqual([(ln.tag, ln.text) for ln in h.lines], [("-", "a\n"), ("+", "A\n"), (" ", "b")])
        h = parse("--- a\n+++ b\n@@ -1,2 +1,1 @@\n-a\n\\ No newline at end of file\n-b\n+c\n")[0].hunks[0]
        self.assertEqual([(ln.tag, ln.text) for ln in h.lines], [("-", "a"), ("-", "b\n"), ("+", "c\n")])

    def test_header_only_file_patch(self):
        fps = parse("--- /dev/null\n+++ b/empty.txt\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertEqual([(fp.old_name, fp.new_name, len(fp.hunks)) for fp in fps],
                         [("/dev/null", "b/empty.txt", 0), ("a/x", "b/x", 1)])

    def test_extra_lines_after_the_counts_are_ignored(self):
        fps = parse("--- a\n+++ b\n@@ -1 +1 @@\n-a\n+b\nthis is not part of the hunk\n")
        self.assertEqual(len(fps[0].hunks[0].lines), 2)

    def test_no_trailing_newline_in_patch_text(self):
        self.assertEqual(len(parse("--- a\n+++ b\n@@ -1 +1 @@\n-a\n+b")[0].hunks[0].lines), 2)

    def test_errors(self):
        bad = {
            "truncated": "--- a\n+++ b\n@@ -1,3 +1,3 @@\n a\n-b\n",
            "bad char": "--- a\n+++ b\n@@ -1,2 +1,2 @@\n a\n*b\n",
            "too many old": "--- a\n+++ b\n@@ -1,1 +1,2 @@\n-a\n-b\n+c\n+d\n",
            "marker first": "--- a\n+++ b\n@@ -1 +1 @@\n\\ No newline at end of file\n-a\n+b\n",
            "bad header": "--- a\n+++ b\n@@ -x +1 @@\n-a\n+b\n",
            "no header": "@@ -1 +1 @@\n-a\n+b\n",
            "no plus": "--- a\nnot a plus line\n",
        }
        for name, text in bad.items():
            with self.subTest(name):
                with self.assertRaises(ParseError):
                    parse(text)

    def test_error_line_numbers(self):
        with self.assertRaises(ParseError) as ctx:
            parse("--- a\n+++ b\n@@ -1,2 +1,2 @@\n a\n*b\n")
        self.assertEqual(ctx.exception.line, 5)
        with self.assertRaises(ParseError) as ctx:
            parse("junk\n--- a\nnot plus\n")
        self.assertEqual(ctx.exception.line, 2)


class TestApplyFile(unittest.TestCase):
    def test_exact_apply(self):
        old, new = "a\nb\nc\nd\n", "a\nB\nc\nd\n"
        res = apply_file(old, one(old, new))
        self.assertEqual(res.text, new)
        self.assertEqual([tuple(h) for h in res.hunks], [(1, 0, 0)])

    def test_no_hunks_returns_the_text(self):
        res = apply_file("x\n", FilePatch("a", "b", []))
        self.assertEqual((res.text, res.hunks), ("x\n", []))

    def test_offsets_forward_and_backward(self):
        old = "".join("l%d\n" % i for i in range(1, 11))
        new = old.replace("l5\n", "L5\n")
        fp = one(old, new)
        res = apply_file("p\nq\n" + old, fp)
        self.assertEqual(res.text, "p\nq\n" + new)
        self.assertEqual((res.hunks[0].offset, res.hunks[0].fuzz), (2, 0))
        short = "".join("l%d\n" % i for i in range(2, 11))
        res = apply_file(short, fp)
        self.assertEqual((res.text, res.hunks[0].offset), (short.replace("l5\n", "L5\n"), -1))

    def test_nearest_candidate_wins_and_forward_wins_ties(self):
        fp = FilePatch("a", "b", [Hunk(3, 1, 3, 1, [Line("-", "x\n"), Line("+", "Z\n")])])
        text = "a\nx\na\nx\na\n"
        res = apply_file(text, fp)
        self.assertEqual(res.text, "a\nx\na\nZ\na\n")
        self.assertEqual(res.hunks[0].offset, 1)
        res = apply_file("x\na\na\na\nx\n", fp)  # x at 0 (offset -2) and at 4 (offset +2): forward wins
        self.assertEqual(res.text, "x\na\na\na\nZ\n")
        res = apply_file("x\na\na\na\na\na\nx\n", fp)  # -2 vs +4: the nearer one wins
        self.assertEqual(res.text, "Z\na\na\na\na\na\nx\n")

    def test_later_hunks_start_from_the_previous_offset(self):
        old = "one\ntwo\nthree\nx\nfive\n"
        new = "ONE\ntwo\nthree\nX\nfive\n"
        fp = one(old, new, context=0)
        self.assertEqual(len(fp.hunks), 2)
        target = "pad\npad\none\nx\ntwo\nthree\nx\nfive\n"
        res = apply_file(target, fp)
        self.assertEqual(res.text, "pad\npad\nONE\nx\ntwo\nthree\nX\nfive\n")
        self.assertEqual([h.offset for h in res.hunks], [2, 3])

    def test_hunks_cannot_match_before_the_previous_hunk(self):
        fp = FilePatch("a", "b", [Hunk(5, 1, 5, 1, [Line("-", "x\n"), Line("+", "X\n")]),
                                  Hunk(6, 1, 6, 1, [Line("-", "y\n"), Line("+", "Y\n")])])
        with self.assertRaises(PatchFailed) as ctx:
            apply_file("y\na\na\na\nx\n", fp)
        self.assertEqual(ctx.exception.failed, [2])

    def test_failure_lists_every_failed_hunk_and_returns_nothing(self):
        old = "".join("l%d\n" % i for i in range(1, 31))
        new = old.replace("l3\n", "L3\n").replace("l15\n", "L15\n").replace("l28\n", "L28\n")
        fp = one(old, new)
        self.assertEqual(len(fp.hunks), 3)
        target = old.replace("l3\n", "gone\n").replace("l28\n", "gone\n")
        with self.assertRaises(PatchFailed) as ctx:
            apply_file(target, fp, max_fuzz=0)
        self.assertEqual(ctx.exception.failed, [1, 3])
        self.assertIsNone(ctx.exception.path)
        self.assertIsInstance(ctx.exception, Exception)

    def test_fuzz_never_drops_more_than_max_fuzz(self):
        old = "a\nb\nc\nd\ne\nf\ng\n"
        fp = one(old, old.replace("d\n", "D\n"))
        target = "a\nb\nXX\nd\ne\nf\ng\n"  # the line just before the change differs
        for fuzz in (0, 1, 2):
            with self.assertRaises(PatchFailed):
                apply_file(target, fp, max_fuzz=fuzz)
        res = apply_file(target, fp, max_fuzz=3)
        self.assertEqual((res.text, res.hunks[0].fuzz), ("a\nb\nXX\nD\ne\nf\ng\n", 3))

    def test_fuzz_levels(self):
        old = "a\nb\nc\nd\ne\nf\ng\n"
        fp = one(old, old.replace("d\n", "D\n"))
        for target, fuzz in (("a\nb\nc\nd\ne\nf\nZ\n", 1), ("a\nb\nc\nd\ne\nY\nZ\n", 2), ("X\nb\nc\nd\ne\nf\ng\n", 1),
                             ("X\nY\nc\nd\ne\nf\ng\n", 2)):
            with self.subTest(target=target):
                res = apply_file(target, fp)
                self.assertEqual(res.hunks[0].fuzz, fuzz)
                self.assertEqual(res.text, target.replace("d\n", "D\n"))
        with self.assertRaises(PatchFailed):
            apply_file("X\nY\nZ\nd\ne\nf\ng\n", fp)  # needs fuzz 3
        with self.assertRaises(PatchFailed):
            apply_file("a\nb\nc\nd\ne\nf\nZ\n", fp, max_fuzz=0)
        self.assertEqual(apply_file("X\nY\nZ\nd\ne\nf\ng\n", fp, max_fuzz=3).hunks[0].fuzz, 3)

    def test_exact_match_at_an_offset_beats_fuzz_at_the_nominal_position(self):
        fp = FilePatch("a", "b", [Hunk(1, 3, 1, 3, [Line(" ", "c1\n"), Line("-", "t\n"), Line("+", "T\n"),
                                                    Line(" ", "d1\n")])])
        res = apply_file("cX\nt\nd1\npad\nc1\nt\nd1\n", fp)
        self.assertEqual(res.text, "cX\nt\nd1\npad\nc1\nT\nd1\n")
        self.assertEqual((res.hunks[0].offset, res.hunks[0].fuzz), (4, 0))

    def test_fuzz_offset_counts_dropped_leading_context(self):
        fp = FilePatch("a", "b", [Hunk(2, 3, 2, 3, [Line(" ", "c1\n"), Line("-", "t\n"), Line("+", "T\n"),
                                                    Line(" ", "d1\n")])])
        res = apply_file("pad\ncX\nt\nd1\n", fp)
        self.assertEqual((res.text, res.hunks[0].offset, res.hunks[0].fuzz), ("pad\ncX\nT\nd1\n", 0, 1))

    def test_missing_newline_at_end_must_match(self):
        old, new = "a\nb\nc", "a\nB\nc"
        fp = one(old, new)
        self.assertEqual(apply_file(old, fp).text, new)
        with self.assertRaises(PatchFailed):
            apply_file("a\nb\nc\n", fp, max_fuzz=0)
        res = apply_file("a\nb\nc\n", fp)
        self.assertEqual((res.text, res.hunks[0].fuzz), ("a\nB\nc\n", 1))

    def test_adding_the_final_newline(self):
        fp = one("a\nb", "a\nb\n")
        self.assertEqual(apply_file("a\nb", fp).text, "a\nb\n")
        with self.assertRaises(PatchFailed):
            apply_file("a\nb\n", fp)

    def test_pure_insertions(self):
        fp = one("a\nb\n", "a\nX\nb\n", context=0)
        self.assertEqual(apply_file("a\nb\n", fp).text, "a\nX\nb\n")
        fp = one("a\nb\n", "X\na\nb\n", context=0)
        self.assertEqual(apply_file("a\nb\n", fp).text, "X\na\nb\n")
        fp = one("", "x\ny\n")
        self.assertEqual(apply_file("", fp).text, "x\ny\n")

    def test_two_hunks_with_pure_insertions(self):
        old = "a\nb\nc\nd\n"
        new = "a\nX\nb\nc\nY\nd\n"
        fp = one(old, new, context=0)
        res = apply_file(old, fp)
        self.assertEqual(res.text, new)
        self.assertEqual([h.index for h in res.hunks], [1, 2])

    def test_deleting_everything(self):
        self.assertEqual(apply_file("x\ny\n", one("x\ny\n", "")).text, "")

    def test_lines_must_match_exactly_including_carriage_returns(self):
        fp = one("a\nb\n", "a\nB\n")
        with self.assertRaises(PatchFailed):
            apply_file("a\r\nb\r\n", fp)
        crlf = one("a\r\nb\r\n", "a\r\nB\r\n")
        self.assertEqual(apply_file("a\r\nb\r\n", crlf).text, "a\r\nB\r\n")

    def test_roundtrip_on_generated_texts(self):
        rng = random.Random(1234)
        for case in range(60):
            n = rng.randint(0, 40)
            old = [rng.choice("abcdefgh") * rng.randint(1, 2) + "\n" for _ in range(n)]
            new = list(old)
            for _ in range(rng.randint(0, 6)):
                op = rng.choice("ird")
                at = rng.randint(0, len(new))
                if op == "i":
                    new.insert(at, "new%d\n" % rng.randint(0, 99))
                elif op == "r" and new:
                    new[min(at, len(new) - 1)] = "rep%d\n" % rng.randint(0, 99)
                elif op == "d" and new:
                    del new[min(at, len(new) - 1)]
            a, b = "".join(old), "".join(new)
            if rng.random() < 0.3:
                a, b = a.rstrip("\n"), b.rstrip("\n")
            ctx = rng.choice([0, 1, 3])
            with self.subTest(case=case):
                text = make_diff(a, b, context=ctx)
                fps = parse(text)
                if a == b:
                    self.assertEqual(fps, [])
                    continue
                self.assertEqual(apply_file(a, fps[0], max_fuzz=0).text, b)
                self.assertEqual(apply_file(b, fps[0].reversed(), max_fuzz=0).text, a)


class TreeBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

    def put(self, tree):
        for path, text in tree.items():
            full = os.path.join(self.root, *path.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(text.encode("utf-8"))

    def snapshot(self):
        out = {}
        for base, _, files in os.walk(self.root):
            for f in files:
                full = os.path.join(base, f)
                with open(full, "rb") as fh:
                    out[os.path.relpath(full, self.root).replace(os.sep, "/")] = fh.read().decode("utf-8")
        return out

    def apply(self, patch, **kw):
        return apply_patch_text(patch, self.root, **kw)


class TestApplyPatchText(TreeBase):
    OLD = {"src/a.py": "x = 1\ny = 2\nz = 3\n", "src/b.py": "def f():\n    return 1\n", "keep.txt": "same\n"}
    NEW = {"src/a.py": "x = 1\ny = 20\nz = 3\n", "src/c.py": "new file\nno newline", "keep.txt": "same\n"}

    def test_modify_create_delete(self):
        self.put(self.OLD)
        results = self.apply(make_tree_diff(self.OLD, self.NEW))
        self.assertEqual(self.snapshot(), self.NEW)
        self.assertEqual([(r.path, r.action) for r in results],
                         [("src/a.py", "modify"), ("src/b.py", "delete"), ("src/c.py", "create")])
        self.assertEqual([tuple(h) for h in results[0].hunks], [(1, 0, 0)])

    def test_create_makes_parent_directories(self):
        self.apply(make_tree_diff({}, {"deep/er/file.txt": "hi\n"}))
        self.assertEqual(self.snapshot(), {"deep/er/file.txt": "hi\n"})

    def test_strip_levels(self):
        self.put({"x.txt": "a\n"})
        self.apply("--- a/x.txt\n+++ b/x.txt\n@@ -1 +1 @@\n-a\n+b\n", strip=1)
        self.apply("--- x.txt\n+++ x.txt\n@@ -1 +1 @@\n-b\n+c\n", strip=0)
        self.put({"p/q/y.txt": "a\n"})
        self.apply("--- one/two/p/q/y.txt\n+++ one/two/p/q/y.txt\n@@ -1 +1 @@\n-a\n+b\n", strip=2)
        self.assertEqual(self.snapshot(), {"x.txt": "c\n", "p/q/y.txt": "b\n"})

    def test_new_name_is_used_for_modifications(self):
        self.put({"new.txt": "a\n"})
        res = self.apply("--- a/old.txt\n+++ b/new.txt\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertEqual((res[0].path, self.snapshot()), ("new.txt", {"new.txt": "b\n"}))

    def test_dry_run_writes_nothing(self):
        self.put(self.OLD)
        res = self.apply(make_tree_diff(self.OLD, self.NEW), dry_run=True)
        self.assertEqual(len(res), 3)
        self.assertEqual(self.snapshot(), self.OLD)

    def test_nothing_is_written_when_any_file_fails(self):
        self.put(self.OLD)
        patch = make_tree_diff(self.OLD, self.NEW)
        self.put({"src/b.py": "def f():\n    return 'edited elsewhere'\n"})
        before = self.snapshot()
        with self.assertRaises(PatchFailed) as ctx:
            self.apply(patch)
        self.assertEqual((ctx.exception.path, ctx.exception.failed), ("src/b.py", [1]))
        self.assertEqual(self.snapshot(), before)

    def test_first_error_in_patch_order_is_raised(self):
        self.put({"a.txt": "x\n"})
        patch = ("--- a/missing.txt\n+++ b/missing.txt\n@@ -1 +1 @@\n-x\n+y\n"
                 "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-nope\n+y\n")
        with self.assertRaises(MissingFile) as ctx:
            self.apply(patch)
        self.assertEqual(ctx.exception.path, "missing.txt")

    def test_create_over_existing_file(self):
        self.put({"a.txt": "x\n"})
        with self.assertRaises(FileExists) as ctx:
            self.apply(make_tree_diff({}, {"a.txt": "y\n"}))
        self.assertEqual(ctx.exception.path, "a.txt")
        self.assertEqual(self.snapshot(), {"a.txt": "x\n"})

    def test_delete_missing_file(self):
        with self.assertRaises(MissingFile):
            self.apply(make_tree_diff({"gone.txt": "x\n"}, {}))

    def test_unsafe_paths(self):
        self.put({"x.txt": "a\n"})
        for patch, strip in (("--- a/../x.txt\n+++ b/../x.txt\n@@ -1 +1 @@\n-a\n+b\n", 1),
                             ("--- /etc/x\n+++ /etc/x\n@@ -1 +1 @@\n-a\n+b\n", 0),
                             ("--- x.txt\n+++ x.txt\n@@ -1 +1 @@\n-a\n+b\n", 1),
                             ("--- a/b/../../x.txt\n+++ a/b/../../x.txt\n@@ -1 +1 @@\n-a\n+b\n", 2)):
            with self.subTest(patch=patch):
                with self.assertRaises(UnsafePath):
                    self.apply(patch, strip=strip)
        self.assertEqual(self.snapshot(), {"x.txt": "a\n"})

    def test_duplicate_targets(self):
        self.put({"x.txt": "a\n"})
        one_file = "--- a/x.txt\n+++ b/x.txt\n@@ -1 +1 @@\n-a\n+b\n"
        with self.assertRaises(DuplicateTarget) as ctx:
            self.apply(one_file + one_file)
        self.assertEqual(ctx.exception.path, "x.txt")
        self.assertEqual(self.snapshot(), {"x.txt": "a\n"})

    def test_reverse_restores_everything(self):
        self.put(self.OLD)
        patch = make_tree_diff(self.OLD, self.NEW)
        self.apply(patch)
        res = self.apply(patch, reverse=True)
        self.assertEqual(self.snapshot(), self.OLD)
        self.assertEqual(sorted((r.path, r.action) for r in res),
                         [("src/a.py", "modify"), ("src/b.py", "create"), ("src/c.py", "delete")])

    def test_fuzz_and_offsets_apply_to_files(self):
        old = "".join("line %d\n" % i for i in range(1, 21))
        self.put({"f.txt": "header\n" + old.replace("line 7\n", "line seven\n")})
        patch = make_tree_diff({"f.txt": old}, {"f.txt": old.replace("line 10\n", "LINE 10\n")})
        res = self.apply(patch)
        self.assertEqual(self.snapshot()["f.txt"], "header\n" + old.replace("line 7\n", "line seven\n").replace("line 10\n", "LINE 10\n"))
        self.assertEqual(tuple(res[0].hunks[0]), (1, 1, 1))
        with self.assertRaises(PatchFailed):
            self.put({"f.txt": "header\n" + old.replace("line 7\n", "line seven\n")})
            self.apply(patch, max_fuzz=0)

    def test_line_endings_and_utf8_are_preserved(self):
        old = {"w.txt": "café\r\nb\r\n", "u.txt": "héllo\nwörld\n"}
        new = {"w.txt": "café\r\nB\r\n", "u.txt": "héllo\nWÖRLD\n"}
        self.put(old)
        self.apply(make_tree_diff(old, new))
        self.assertEqual(self.snapshot(), new)

    def test_external_patch_text_with_timestamps_and_prose(self):
        self.put({"hello.txt": "hello\nworld\n"})
        patch = ("From: someone\nSubject: [PATCH] greet\n\ndiff --git a/hello.txt b/hello.txt\nindex 1..2 100644\n"
                 "--- a/hello.txt\t2026-01-01 00:00:00.000000000 +0000\n+++ b/hello.txt\t2026-01-02 00:00:00.000000000 +0000\n"
                 "@@ -1,2 +1,2 @@\n hello\n-world\n+there\n-- \n2.40.0\n")
        self.apply(patch)
        self.assertEqual(self.snapshot(), {"hello.txt": "hello\nthere\n"})


class TestMakeTreeDiff(TreeBase):
    def test_exact_output(self):
        out = make_tree_diff({"b.txt": "1\n", "a.txt": "x\n", "same": "s\n"},
                             {"b.txt": "2\n", "c.txt": "new\n", "same": "s\n"})
        self.assertEqual(out, "--- a/a.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
                              "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-1\n+2\n"
                              "--- /dev/null\n+++ b/c.txt\n@@ -0,0 +1 @@\n+new\n")

    def test_no_differences(self):
        self.assertEqual(make_tree_diff({"a": "x\n"}, {"a": "x\n"}), "")
        self.assertEqual(make_tree_diff({}, {}), "")

    def test_empty_files_have_headers_only(self):
        self.assertEqual(make_tree_diff({}, {"e.txt": ""}), "--- /dev/null\n+++ b/e.txt\n")
        self.assertEqual(make_tree_diff({"e.txt": ""}, {}), "--- a/e.txt\n+++ /dev/null\n")

    def test_context_argument(self):
        old = {"f": "a\nb\nc\nd\ne\n"}
        new = {"f": "a\nb\nC\nd\ne\n"}
        self.assertEqual(make_tree_diff(old, new, context=0), "--- a/f\n+++ b/f\n@@ -3 +3 @@\n-c\n+C\n")

    def test_roundtrip_through_apply(self):
        old = {"a.txt": "one\ntwo\n", "dir/b.txt": "no newline", "gone.txt": "bye\n", "empty.txt": ""}
        new = {"a.txt": "one\n2\nthree\n", "dir/b.txt": "no newline!\n", "fresh.txt": "", "dir/n/c.txt": "c"}
        self.put(old)
        self.apply(make_tree_diff(old, new))
        self.assertEqual(self.snapshot(), new)


if __name__ == "__main__":
    unittest.main()

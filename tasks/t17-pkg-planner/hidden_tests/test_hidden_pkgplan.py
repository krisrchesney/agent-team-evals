"""Hidden grader for t17. Test names start with the requirement (R1..R28) they check."""
import contextlib
import io
import json
import os
import random
import tempfile
import unittest
from fractions import Fraction

from pkgplan import (Constraint, ConstraintError, LockError, Registry, ResolutionError, Version, VersionError,
                     build_plan, dump_lock, format_report, format_size, load_lock, main, parse_requirement, resolve)


def P(deps=None, size=0, yanked=False):
    return {"deps": deps or {}, "size": size, "yanked": yanked}


def reg(spec):
    return Registry.from_dict(spec)


def pick(resolved):
    return [f"{p.name} {p.version}" for p in resolved]


def plan(spec, requirements, installed=None, **kw):
    registry = reg(spec)
    resolved = resolve(registry, requirements, installed=installed, **kw)
    return build_plan(resolved, installed)


def report(spec, requirements, installed=None, **kw):
    return format_report(plan(spec, requirements, installed, **kw))


def v(text):
    return Version(text)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, out, err)
    return code, out.getvalue(), err.getvalue()


class Case(unittest.TestCase):
    """TestCase whose subTest stops at the first failure (so a failing test counts once) but names the case."""

    @contextlib.contextmanager
    def subTest(self, msg=None, **params):
        try:
            yield
        except AssertionError as exc:
            raise AssertionError(f"{msg or ''} {params}: {exc}") from None


# ---------------------------------------------------------------------------------------------------------
# Versions (R1-R3)
# ---------------------------------------------------------------------------------------------------------

class HiddenVersions(Case):
    def test_r1_parse_fields(self):
        x = v("1.2.3-rc.1+build.5")
        self.assertEqual((x.major, x.minor, x.patch, x.prerelease, x.build), (1, 2, 3, "rc.1", "build.5"))
        self.assertTrue(x.is_prerelease)
        y = v("10.0.7")
        self.assertEqual((y.major, y.minor, y.patch, y.prerelease, y.build), (10, 0, 7, None, None))
        self.assertFalse(y.is_prerelease)
        z = v("0.0.1+only.build")
        self.assertEqual((z.prerelease, z.build), (None, "only.build"))
        self.assertFalse(z.is_prerelease)

    def test_r1_invalid_versions(self):
        for bad in ["", "1", "1.2", "1.2.3.4", "v1.2.3", "1.2.x", "1.2.3-", "1.2.3+", "1.2.3-a..b", "a.b.c",
                    "1.2.-3", "-1.2.3", "1.2.3-rc_1"]:
            with self.subTest(text=bad):
                with self.assertRaises(VersionError):
                    Version(bad)
        self.assertTrue(issubclass(VersionError, ValueError))

    def test_r2_prerelease_below_release(self):
        self.assertLess(v("1.0.0-rc.1"), v("1.0.0"))
        self.assertLess(v("1.0.0-zzz"), v("1.0.0"))
        self.assertGreater(v("1.0.1-alpha"), v("1.0.0"))

    def test_r2_numeric_parts_compare_as_numbers(self):
        self.assertLess(v("1.9.0"), v("1.10.0"))
        self.assertLess(v("1.2.9"), v("1.2.10"))
        self.assertLess(v("2.0.0"), v("10.0.0"))

    def test_r2_prerelease_identifiers(self):
        ordered = ["0.9.9", "1.0.0-1", "1.0.0-2", "1.0.0-10", "1.0.0-Beta", "1.0.0-alpha", "1.0.0-alpha.1",
                   "1.0.0-alpha.2", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11",
                   "1.0.0-rc.1", "1.0.0", "1.0.1", "1.1.0", "2.0.0", "10.0.0"]
        versions = [v(t) for t in ordered]
        for i, low in enumerate(versions):
            for high in versions[i + 1:]:
                with self.subTest(low=str(low), high=str(high)):
                    self.assertLess(low, high)
                    self.assertGreater(high, low)
        shuffled = versions[:]
        random.Random(2).shuffle(shuffled)
        self.assertEqual([str(x) for x in sorted(shuffled)], ordered)

    def test_r2_rc2_below_rc10_and_shorter_is_lower(self):
        self.assertLess(v("1.0.0-rc.2"), v("1.0.0-rc.10"))
        self.assertLess(v("1.0.0-rc"), v("1.0.0-rc.1"))
        self.assertLess(v("1.0.0-rc.1"), v("1.0.0-rc.1.0"))

    def test_r2_random_pairs_match_precedence_rules(self):
        rng = random.Random(21)

        def make():
            parts = [rng.randint(0, 2) for _ in range(3)]
            pre = None
            if rng.random() < 0.7:
                pre = [rng.choice(["0", "1", "2", "10", "a", "b", "B", "rc", "x-1"]) for _ in range(rng.randint(1, 3))]
            return parts, pre

        def cmp(a, b):
            if a[0] != b[0]:
                return -1 if a[0] < b[0] else 1
            if a[1] is None or b[1] is None:
                return 0 if a[1] is b[1] else (1 if a[1] is None else -1)
            for x, y in zip(a[1], b[1]):
                if x == y:
                    continue
                if x.isdigit() and y.isdigit():
                    return -1 if int(x) < int(y) else 1
                if x.isdigit() != y.isdigit():
                    return -1 if x.isdigit() else 1
                return -1 if x < y else 1
            return (len(a[1]) > len(b[1])) - (len(a[1]) < len(b[1]))

        def text(item):
            parts, pre = item
            return ".".join(map(str, parts)) + ("-" + ".".join(pre) if pre else "")

        for _ in range(600):
            a, b = make(), make()
            want = cmp(a, b)
            va, vb = v(text(a)), v(text(b))
            with self.subTest(a=text(a), b=text(b)):
                self.assertEqual((va > vb) - (va < vb), want)
                self.assertEqual(va == vb, want == 0)

    def test_r3_build_metadata_is_ignored(self):
        self.assertEqual(v("1.0.0+a"), v("1.0.0+b"))
        self.assertEqual(v("1.0.0+a"), v("1.0.0"))
        self.assertFalse(v("1.0.0+a") < v("1.0.0+b"))
        self.assertFalse(v("1.0.0+b") < v("1.0.0+a"))
        self.assertEqual(hash(v("1.0.0+a")), hash(v("1.0.0+b")))
        self.assertEqual(len({v("1.0.0+a"), v("1.0.0+b"), v("1.0.0")}), 1)
        self.assertEqual(v("1.0.0-rc.1+x"), v("1.0.0-rc.1+y"))
        self.assertLess(v("1.0.0+zzz"), v("1.0.1+aaa"))

    def test_r3_str_keeps_build_metadata(self):
        self.assertEqual(str(v("1.0.0+Build.7")), "1.0.0+Build.7")
        self.assertEqual(str(v("1.2.3-rc.1+b")), "1.2.3-rc.1+b")
        self.assertEqual(str(v("1.2.3-rc.1")), "1.2.3-rc.1")
        self.assertEqual(str(v("4.5.6")), "4.5.6")


# ---------------------------------------------------------------------------------------------------------
# Constraints (R4-R8)
# ---------------------------------------------------------------------------------------------------------

class HiddenConstraints(Case):
    def check(self, text, yes=(), no=()):
        c = Constraint(text)
        for t in yes:
            with self.subTest(constraint=text, version=t):
                self.assertTrue(c.matches(v(t)), f"{text} should match {t}")
        for t in no:
            with self.subTest(constraint=text, version=t):
                self.assertFalse(c.matches(v(t)), f"{text} should not match {t}")

    def test_r4_comparison_operators(self):
        self.check("==1.2.3", yes=["1.2.3"], no=["1.2.4", "1.2.2"])
        self.check("!=1.2.3", yes=["1.2.4", "1.2.2"], no=["1.2.3"])
        self.check(">=1.2.3", yes=["1.2.3", "1.2.4", "2.0.0"], no=["1.2.2"])
        self.check(">1.2.3", yes=["1.2.4"], no=["1.2.3", "1.2.2"])
        self.check("<=1.2.3", yes=["1.2.3", "1.2.2"], no=["1.2.4"])
        self.check("<1.2.3", yes=["1.2.2", "0.1.0"], no=["1.2.3", "1.2.4"])

    def test_r4_bare_version_means_equals(self):
        self.check("1.2.3", yes=["1.2.3"], no=["1.2.4", "1.2.2"])
        self.check("1", yes=["1.0.0"], no=["1.0.1", "2.0.0"])

    def test_r4_star_matches_everything(self):
        self.check("*", yes=["0.0.1", "99.0.0", "3.0.0-rc.1"])

    def test_r4_clauses_are_anded(self):
        self.check(">=1.0.0,<2.0.0", yes=["1.0.0", "1.5.0"], no=["0.9.9", "2.0.0", "2.5.0"])
        self.check(">=1.0.0,!=1.5.0,<2.0.0", yes=["1.4.0", "1.6.0"], no=["1.5.0", "2.0.0"])
        self.check("*,>=2.0.0", yes=["2.0.0"], no=["1.9.9"])

    def test_r4_whitespace_is_ignored(self):
        self.check(" >= 1.0 , < 2 ", yes=["1.0.0", "1.9.9"], no=["0.9.9", "2.0.0"])
        self.check("> = 1.2.3", yes=["1.2.3"], no=["1.2.2"])
        self.check("^ 1.2.3", yes=["1.9.0"], no=["2.0.0"])

    def test_r4_partial_versions_fill_with_zeros(self):
        self.check(">=1.2", yes=["1.2.0", "1.2.1"], no=["1.1.9"])
        self.check("==1.2", yes=["1.2.0"], no=["1.2.1"])
        self.check("<2", yes=["1.9.9"], no=["2.0.0"])
        self.check("<=1.2", yes=["1.2.0"], no=["1.2.1"])
        self.check(">1", yes=["1.0.1"], no=["1.0.0"])
        self.check("!=1.2", yes=["1.2.1"], no=["1.2.0"])

    def test_r4_invalid_constraints(self):
        for bad in ["", " ", ">=", ">=1.0,,<2", ">=1,", ",>=1", "~=1.0", "=>1.0", "=1.0", "1.0.0.0", ">=*", "^",
                    ">=a.b", "1.x", "<>1"]:
            with self.subTest(text=bad):
                with self.assertRaises(ConstraintError):
                    Constraint(bad)
        self.assertTrue(issubclass(ConstraintError, ValueError))

    def test_r5_caret_ranges(self):
        self.check("^1.2.3", yes=["1.2.3", "1.2.4", "1.9.9"], no=["1.2.2", "2.0.0", "0.9.9"])
        self.check("^0.2.3", yes=["0.2.3", "0.2.9"], no=["0.3.0", "0.2.2", "1.0.0"])
        self.check("^0.0.3", yes=["0.0.3"], no=["0.0.4", "0.0.2", "0.1.0"])
        self.check("^1.2", yes=["1.2.0", "1.9.0"], no=["1.1.9", "2.0.0"])
        self.check("^0.2", yes=["0.2.0", "0.2.5"], no=["0.3.0", "0.1.9"])
        self.check("^0.0", yes=["0.0.0", "0.0.9"], no=["0.1.0"])
        self.check("^1", yes=["1.0.0", "1.9.9"], no=["0.9.9", "2.0.0"])
        self.check("^0", yes=["0.0.0", "0.9.9"], no=["1.0.0"])
        self.check("^0.0.0", yes=["0.0.0"], no=["0.0.1"])

    def test_r5_caret_combines_with_other_clauses(self):
        self.check("^1.2.3,!=1.5.0", yes=["1.4.0", "1.6.0"], no=["1.5.0", "2.0.0"])
        self.check("^1.0.0,<1.5.0", yes=["1.4.9"], no=["1.5.0"])

    def test_r6_tilde_ranges(self):
        self.check("~1.2.3", yes=["1.2.3", "1.2.9"], no=["1.3.0", "1.2.2"])
        self.check("~1.2", yes=["1.2.0", "1.2.9"], no=["1.3.0", "1.1.9"])
        self.check("~1", yes=["1.0.0", "1.9.9"], no=["2.0.0", "0.9.9"])
        self.check("~0.2.3", yes=["0.2.5"], no=["0.3.0", "0.2.2"])
        self.check("~0", yes=["0.0.0", "0.9.9"], no=["1.0.0"])
        self.check("~0.0.3", yes=["0.0.3", "0.0.9"], no=["0.1.0", "0.0.2"])

    def test_r7_caret_and_tilde_bounds_exclude_prereleases_of_the_bound(self):
        self.check("^1.2.3", yes=["1.9.9-beta"], no=["2.0.0-alpha", "2.0.0-0", "2.0.0-rc.1"])
        self.check("~1.2.3", yes=["1.2.9-rc.1"], no=["1.3.0-alpha", "1.3.0"])
        self.check("^0.2.3", no=["0.3.0-rc.1"])
        self.check("^0.0.3", no=["0.0.4-1"])
        self.check("^1", no=["2.0.0-alpha"])
        self.check("~1", no=["2.0.0-alpha"])

    def test_r7_explicit_upper_bound_still_matches_prereleases_of_it(self):
        self.check("<2.0.0", yes=["2.0.0-alpha", "1.9.9"], no=["2.0.0"])
        self.check(">=1.0.0,<2.0.0", yes=["2.0.0-alpha"], no=["2.0.0"])
        self.check("<=2.0.0", yes=["2.0.0-alpha", "2.0.0"])

    def test_r7_caret_with_prerelease_operand(self):
        self.check("^1.0.0-beta.2", yes=["1.0.0-beta.2", "1.0.0-beta.3", "1.0.0", "1.5.0"],
                   no=["1.0.0-beta.1", "2.0.0-alpha", "2.0.0"])
        self.check("~2.0.0-rc.1", yes=["2.0.0-rc.2", "2.0.0", "2.0.9"], no=["2.0.0-rc.0", "2.1.0-alpha", "2.1.0"])

    def test_r8_str_is_clauses_without_whitespace(self):
        self.assertEqual(str(Constraint(" >= 1.0 , <2 ")), ">=1.0,<2")
        self.assertEqual(str(Constraint("^ 1.2")), "^1.2")
        self.assertEqual(str(Constraint("*")), "*")
        self.assertEqual(str(Constraint("1.2.3")), "1.2.3")
        self.assertEqual(str(Constraint("== 1.0")), "==1.0")
        self.assertEqual(str(Constraint("~1.2.3 , != 1.2.5")), "~1.2.3,!=1.2.5")
        self.assertEqual(str(Constraint(">=1.0.0")), ">=1.0.0")

    def test_r5_r6_random_ranges_match_bounds(self):
        rng = random.Random(56)
        grid = [Version(f"{a}.{b}.{c}") for a in range(3) for b in range(3) for c in range(3)]
        grid += [Version(f"{a}.{b}.{c}-rc.1") for a in range(3) for b in range(3) for c in range(2)]
        for _ in range(200):
            given = rng.randint(1, 3)
            nums = [rng.randint(0, 2) for _ in range(given)]
            op = rng.choice("^~")
            text = op + ".".join(map(str, nums))
            full = nums + [0] * (3 - given)
            if op == "^":
                bump = next((i for i in range(given) if nums[i]), given - 1)
            else:
                bump = 0 if given == 1 else 1
            upper = full[:bump] + [full[bump] + 1] + [0] * (2 - bump)
            lower_v = Version(".".join(map(str, full)))
            upper_v = Version(".".join(map(str, upper)))
            c = Constraint(text)
            for x in grid:
                want = x >= lower_v and x < upper_v and not (
                    x.prerelease is not None and (x.major, x.minor, x.patch) == (upper[0], upper[1], upper[2]))
                with self.subTest(constraint=text, version=str(x)):
                    self.assertEqual(c.matches(x), want)


# ---------------------------------------------------------------------------------------------------------
# Registry (R9, R10)
# ---------------------------------------------------------------------------------------------------------

class HiddenRegistry(Case):
    def test_r9_lookup_ignores_case_and_separators(self):
        r = Registry()
        r.add("Foo_Bar", "1.0.0")
        for spelling in ["foo-bar", "FOO.BAR", "foo__bar", "Foo_Bar", "foo-.bar", " foo-bar "]:
            with self.subTest(spelling=spelling):
                self.assertIn(spelling, r)
                self.assertEqual(r.display_name(spelling), "Foo_Bar")
                self.assertEqual([str(p.version) for p in r.versions(spelling)], ["1.0.0"])
                self.assertIsNotNone(r.get(spelling, v("1.0.0")))
        self.assertNotIn("foobar", r)
        self.assertNotIn("foo-baz", r)

    def test_r9_display_name_is_first_spelling(self):
        r = Registry()
        r.add("Web_Core", "1.0.0")
        r.add("web-core", "2.0.0")
        r.add("WEB.CORE", "3.0.0")
        self.assertEqual(r.names(), ["Web_Core"])
        self.assertEqual([str(p.version) for p in r.versions("web.core")], ["3.0.0", "2.0.0", "1.0.0"])
        self.assertTrue(all(p.name == "Web_Core" for p in r.versions("web-core")))

    def test_r9_from_dict_merges_spellings(self):
        r = reg({"Web": {"1.0.0": P()}, "web": {"2.0.0": P()}})
        self.assertEqual(r.names(), ["Web"])
        self.assertEqual(len(r.versions("WEB")), 2)

    def test_r9_names_sorted_by_lookup_key(self):
        r = Registry()
        for name in ["Zeta", "alpha", "Mid_Pkg", "beta"]:
            r.add(name, "1.0.0")
        self.assertEqual(r.names(), ["alpha", "beta", "Mid_Pkg", "Zeta"])

    def test_r9_unknown_package_lookups(self):
        r = Registry()
        r.add("a", "1.0.0")
        self.assertNotIn("b", r)
        self.assertIsNone(r.get("b", v("1.0.0")))
        self.assertIsNone(r.get("a", v("9.9.9")))
        with self.assertRaises(KeyError):
            r.versions("b")

    def test_r9_search_is_a_prefix_match_on_lookup_keys(self):
        r = Registry()
        for name in ["Foo_Bar", "foo-baz", "other", "Zfoo"]:
            r.add(name, "1.0.0")
        self.assertEqual(r.search("FOO"), ["Foo_Bar", "foo-baz"])
        self.assertEqual(r.search("foo_ba"), ["Foo_Bar", "foo-baz"])
        self.assertEqual(r.search("bar"), [])
        self.assertEqual(r.search("oth"), ["other"])
        self.assertEqual(r.search(""), ["Foo_Bar", "foo-baz", "other", "Zfoo"])

    def test_r10_size_must_be_a_non_negative_int(self):
        r = Registry()
        for bad in (-1, 1.5, "5", None):
            with self.subTest(size=bad):
                with self.assertRaises(ValueError):
                    r.add("p", "1.0.0", size=bad)
        self.assertNotIn("p", r)
        r.add("p", "1.0.0", size=0)
        r.add("p", "1.1.0", size=10)
        with self.assertRaises(ValueError):
            r.add("p", "1.2.0", size=-5)
        self.assertEqual([str(x.version) for x in r.versions("p")], ["1.1.0", "1.0.0"])

    def test_r10_duplicate_versions_are_rejected(self):
        r = Registry()
        r.add("p", "1.0.0")
        with self.assertRaises(ValueError):
            r.add("P", "1.0.0")
        with self.assertRaises(ValueError):
            r.add("p", "1.0.0+other")
        r.add("p", "1.0.1")
        self.assertEqual(len(r.versions("p")), 2)

    def test_r10_from_dict_defaults(self):
        r = reg({"p": {"1.0.0": {}}})
        pv = r.versions("p")[0]
        self.assertEqual((pv.deps, pv.size, pv.yanked), ({}, 0, False))
        r2 = reg({"p": {"1.0.0": P({"q": "^1"}, size=7, yanked=True)}, "q": {"1.0.0": P()}})
        pv2 = r2.versions("p")[0]
        self.assertEqual((pv2.deps, pv2.size, pv2.yanked), ({"q": "^1"}, 7, True))


# ---------------------------------------------------------------------------------------------------------
# Resolution (R11-R17)
# ---------------------------------------------------------------------------------------------------------

LIB = {"lib": {"1.0.0": P(), "1.4.0": P(), "1.5.0": P(), "2.0.0": P()}}


class HiddenResolve(Case):
    def test_r11_roots_first_then_dependencies_alphabetically(self):
        spec = {
            "zeta": {"1.0.0": P({"Zed": "*", "apple": "*"})},
            "alpha": {"1.0.0": P({"apple": "*", "mid": "*"})},
            "apple": {"1.0.0": P()}, "Zed": {"1.0.0": P()}, "mid": {"1.0.0": P()},
        }
        got = pick(resolve(reg(spec), ["zeta", "alpha"]))
        self.assertEqual(got, ["zeta 1.0.0", "alpha 1.0.0", "apple 1.0.0", "Zed 1.0.0", "mid 1.0.0"])

    def test_r11_each_package_appears_once(self):
        spec = {
            "a": {"1.0.0": P({"c": "*", "b": "*"})}, "b": {"1.0.0": P({"c": "*"})}, "c": {"1.0.0": P()},
        }
        self.assertEqual(pick(resolve(reg(spec), ["a", "c", "b"])), ["a 1.0.0", "c 1.0.0", "b 1.0.0"])

    def test_r11_same_package_requested_twice_merges_constraints(self):
        got = resolve(reg(LIB), ["lib>=1.0.0", "LIB<2.0.0"])
        self.assertEqual(pick(got), ["lib 1.5.0"])

    def test_r11_requirement_text_forms(self):
        self.assertEqual(pick(resolve(reg(LIB), ["lib >= 1.0.0 , < 2.0.0"])), ["lib 1.5.0"])
        self.assertEqual(pick(resolve(reg(LIB), ["lib"])), ["lib 2.0.0"])
        self.assertEqual(pick(resolve(reg(LIB), ["  lib^1.4"])), ["lib 1.5.0"])

    def test_r11_returns_package_versions(self):
        spec = {"app": {"1.0.0": P({"lib": "*"}, size=42, yanked=False)}, "lib": {"2.0.0": P()}}
        app, lib = resolve(reg(spec), ["app"])
        self.assertEqual((app.name, str(app.version), app.deps, app.size, app.yanked), ("app", "1.0.0", {"lib": "*"}, 42, False))
        self.assertEqual((lib.name, str(lib.version)), ("lib", "2.0.0"))

    def test_r11_names_in_any_spelling_resolve_to_the_same_package(self):
        spec = {"Foo_Bar": {"1.0.0": P()}, "app": {"1.0.0": P({"foo.bar": "*"})}}
        self.assertEqual(pick(resolve(reg(spec), ["app", "FOO-BAR"])), ["app 1.0.0", "Foo_Bar 1.0.0"])

    def test_r12_highest_satisfying_version(self):
        self.assertEqual(pick(resolve(reg(LIB), ["lib<1.5.0"])), ["lib 1.4.0"])
        self.assertEqual(pick(resolve(reg(LIB), ["lib"])), ["lib 2.0.0"])
        self.assertEqual(pick(resolve(reg(LIB), ["lib==1.0.0"])), ["lib 1.0.0"])
        self.assertEqual(pick(resolve(reg(LIB), ["lib^1.0"])), ["lib 1.5.0"])
        self.assertEqual(pick(resolve(reg(LIB), ["lib~1.4"])), ["lib 1.4.0"])

    def test_r12_constraints_seen_before_choosing_are_merged(self):
        spec = dict(LIB, app={"1.0.0": P({"lib": "<1.5.0"})})
        self.assertEqual(pick(resolve(reg(spec), ["app", "lib>=1.0.0"])), ["app 1.0.0", "lib 1.4.0"])
        spec2 = dict(LIB, a1={"1.0.0": P({"lib": ">=1.2"})}, a2={"1.0.0": P({"lib": "<1.5"})})
        self.assertEqual(pick(resolve(reg(spec2), ["a1", "a2"])), ["a1 1.0.0", "a2 1.0.0", "lib 1.4.0"])

    def test_r12_a_chosen_package_is_never_revisited(self):
        spec = dict(LIB, app={"1.0.0": P({"lib": "<1.5.0"})})
        with self.assertRaises(ResolutionError):
            resolve(reg(spec), ["lib", "app"])
        # the same requirements in the other order work
        self.assertEqual(pick(resolve(reg(spec), ["app", "lib"])), ["app 1.0.0", "lib 1.4.0"])

    def test_r12_transitive_dependencies_are_resolved(self):
        spec = {"a": {"1.0.0": P({"b": "^1"})}, "b": {"1.0.0": P({"c": ">=2"}), "1.2.0": P({"c": ">=3"})},
                "c": {"1.0.0": P(), "2.0.0": P(), "3.5.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["a"])), ["a 1.0.0", "b 1.2.0", "c 3.5.0"])

    def test_r13_prereleases_are_skipped_by_default(self):
        spec = {"p": {"1.0.0": P(), "2.0.0-rc.1": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p"])), ["p 1.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p>=1.0.0"])), ["p 1.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p^1.0.0"])), ["p 1.0.0"])

    def test_r13_prerelease_flag(self):
        spec = {"p": {"1.0.0": P(), "2.0.0-rc.1": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p"], prerelease=True)), ["p 2.0.0-rc.1"])

    def test_r13_prerelease_operand_makes_prereleases_eligible(self):
        spec = {"p": {"1.0.0": P(), "2.0.0-rc.1": P(), "2.0.0-rc.2": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p>=2.0.0-rc.1"])), ["p 2.0.0-rc.2"])
        self.assertEqual(pick(resolve(reg(spec), ["p==2.0.0-rc.1"])), ["p 2.0.0-rc.1"])
        self.assertEqual(pick(resolve(reg(spec), ["p^1.0.0-0"])), ["p 1.0.0"])

    def test_r13_a_dependency_constraint_can_make_prereleases_eligible(self):
        spec = {"p": {"1.0.0": P(), "2.0.0-rc.1": P()}, "app": {"1.0.0": P({"p": ">=2.0.0-rc.1"})}}
        self.assertEqual(pick(resolve(reg(spec), ["app", "p"])), ["app 1.0.0", "p 2.0.0-rc.1"])

    def test_r13_only_prereleases_and_no_permission_means_no_candidate(self):
        spec = {"p": {"2.0.0-rc.1": P()}}
        with self.assertRaises(ResolutionError):
            resolve(reg(spec), ["p"])
        self.assertEqual(pick(resolve(reg(spec), ["p"], prerelease=True)), ["p 2.0.0-rc.1"])

    def test_r13_r7_caret_bound_still_excludes_prereleases_when_allowed(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P(), "2.0.0-alpha": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p^1.0.0"], prerelease=True)), ["p 1.5.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p~1"], prerelease=True)), ["p 1.5.0"])

    def test_r13_r7_explicit_upper_bound_includes_prereleases_when_allowed(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P(), "2.0.0-alpha": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p<2.0.0"], prerelease=True)), ["p 2.0.0-alpha"])
        self.assertEqual(pick(resolve(reg(spec), ["p<2.0.0"])), ["p 1.5.0"])

    def test_r13_caret_with_prerelease_operand_picks_release_over_its_prerelease(self):
        spec = {"p": {"2.0.0-rc.1": P(), "2.0.0-rc.2": P(), "2.0.0": P(), "3.0.0-alpha": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p^2.0.0-rc.1"])), ["p 2.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p^2.0.0-rc.1,<2.0.0"])), ["p 2.0.0-rc.2"])

    def test_r14_yanked_versions_are_skipped(self):
        spec = {"p": {"1.0.0": P(), "2.0.0": P(yanked=True)}}
        self.assertEqual(pick(resolve(reg(spec), ["p"])), ["p 1.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p>=1.0.0"])), ["p 1.0.0"])

    def test_r14_an_exact_pin_allows_a_yanked_version(self):
        spec = {"p": {"1.0.0": P(), "2.0.0": P(yanked=True)}}
        self.assertEqual(pick(resolve(reg(spec), ["p==2.0.0"])), ["p 2.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p>=1.0.0,==2.0.0"])), ["p 2.0.0"])
        spec2 = dict(spec, app={"1.0.0": P({"p": "2.0.0"})})
        self.assertEqual(pick(resolve(reg(spec2), ["app", "p"])), ["app 1.0.0", "p 2.0.0"])

    def test_r14_ranges_and_other_operators_do_not_pin(self):
        spec = {"p": {"1.0.0": P(), "2.0.0": P(yanked=True)}}
        for text in ["p>=2.0.0", "p^2.0.0", "p~2.0", "p<=2.0.0,>=2.0.0", "p!=1.0.0"]:
            with self.subTest(requirement=text):
                with self.assertRaises(ResolutionError):
                    resolve(reg(spec), [text])

    def test_r14_pin_does_not_unlock_other_yanked_versions(self):
        spec = {"p": {"1.0.0": P(yanked=True), "2.0.0": P(yanked=True), "3.0.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p==1.0.0"])), ["p 1.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p<3.0.0,==2.0.0"])), ["p 2.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p"])), ["p 3.0.0"])

    def test_r15_installed_version_is_kept_when_it_satisfies(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p>=1.0.0"], installed={"p": "1.0.0"})), ["p 1.0.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p"], installed={"p": v("1.0.0")})), ["p 1.0.0"])

    def test_r15_installed_version_that_does_not_satisfy_is_replaced(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p>=1.2"], installed={"p": "1.0.0"})), ["p 1.5.0"])

    def test_r15_installed_names_use_any_spelling(self):
        spec = {"Foo_Bar": {"1.0.0": P(), "1.5.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["foo-bar"], installed={"FOO.BAR": "1.0.0"})), ["Foo_Bar 1.0.0"])

    def test_r15_upgrade_and_upgrade_all(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P()}, "q": {"1.0.0": P(), "1.5.0": P()}}
        installed = {"p": "1.0.0", "q": "1.0.0"}
        got = resolve(reg(spec), ["p", "q"], installed=installed, upgrade=["P"])
        self.assertEqual(pick(got), ["p 1.5.0", "q 1.0.0"])
        got = resolve(reg(spec), ["p", "q"], installed=installed, upgrade_all=True)
        self.assertEqual(pick(got), ["p 1.5.0", "q 1.5.0"])
        got = resolve(reg(spec), ["p", "q"], installed=installed, upgrade=["other"])
        self.assertEqual(pick(got), ["p 1.0.0", "q 1.0.0"])

    def test_r15_installed_prerelease_is_kept(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P(), "2.0.0-rc.1": P()}}
        got = resolve(reg(spec), ["p>=1.0.0"], installed={"p": "2.0.0-rc.1"})
        self.assertEqual(pick(got), ["p 2.0.0-rc.1"])
        got = resolve(reg(spec), ["p>=1.0.0"], installed={"p": "2.0.0-rc.1"}, upgrade_all=True)
        self.assertEqual(pick(got), ["p 1.5.0"])

    def test_r15_installed_yanked_version_is_kept(self):
        spec = {"p": {"1.0.0": P(yanked=True), "1.5.0": P()}}
        got = resolve(reg(spec), ["p"], installed={"p": "1.0.0"})
        self.assertEqual(pick(got), ["p 1.0.0"])
        got = resolve(reg(spec), ["p"], installed={"p": "1.0.0"}, upgrade=["p"])
        self.assertEqual(pick(got), ["p 1.5.0"])

    def test_r15_installed_version_unknown_to_the_registry_is_ignored(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p"], installed={"p": "0.5.0"})), ["p 1.5.0"])
        self.assertEqual(pick(resolve(reg(spec), ["p"], installed={"zzz": "1.0.0"})), ["p 1.5.0"])

    def test_r15_installed_version_compared_ignoring_build_metadata(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P()}}
        self.assertEqual(pick(resolve(reg(spec), ["p"], installed={"p": "1.0.0+local"})), ["p 1.0.0"])

    def test_r15_r16_kept_installed_version_can_conflict_with_a_later_requirement(self):
        spec = {"p": {"1.0.0": P(), "1.5.0": P()}, "app": {"1.0.0": P({"p": ">=1.5"})}}
        installed = {"p": "1.0.0"}
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["p", "app"], installed=installed)
        self.assertEqual(str(ctx.exception), "conflict on p: 1.0.0 was chosen for * but >=1.5 is required by app")
        # when the dependent is handled first, the installed version no longer satisfies and is replaced
        got = resolve(reg(spec), ["app", "p"], installed=installed)
        self.assertEqual(pick(got), ["app 1.0.0", "p 1.5.0"])

    def test_r16_conflict_message(self):
        spec = dict(LIB, App={"1.0.0": P({"lib": " < 1.5.0 "})})
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["lib", "App"])
        self.assertEqual(str(ctx.exception), "conflict on lib: 2.0.0 was chosen for * but <1.5.0 is required by App")

    def test_r16_conflict_lists_every_earlier_constraint(self):
        spec = dict(LIB, App={"1.0.0": P({"lib": "<2.0.0"})})
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["lib>=1.0.0", "lib <= 2.0.0", "App"])
        self.assertEqual(str(ctx.exception),
                         "conflict on lib: 2.0.0 was chosen for >=1.0.0,<=2.0.0 but <2.0.0 is required by App")

    def test_r16_conflict_uses_display_names_and_build_metadata(self):
        spec = {"Foo_Bar": {"1.0.0+b7": P()}, "app": {"1.0.0": P({"foo.bar": ">=2"})}}
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["foo-bar", "app"])
        self.assertEqual(str(ctx.exception), "conflict on Foo_Bar: 1.0.0+b7 was chosen for * but >=2 is required by app")

    def test_r16_a_compatible_later_requirement_is_not_a_conflict(self):
        spec = dict(LIB, app={"1.0.0": P({"lib": ">=1.0.0"})})
        self.assertEqual(pick(resolve(reg(spec), ["lib", "app"])), ["lib 2.0.0", "app 1.0.0"])

    def test_r17_no_candidate_message(self):
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(LIB), ["lib>=3.0.0"])
        self.assertEqual(str(ctx.exception), "no version of lib satisfies >=3.0.0 (required by <root>)")

    def test_r17_no_candidate_lists_constraints_and_requirers_once(self):
        spec = dict(LIB, app={"1.0.0": P({"lib": ">=3"})})
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["app", "lib>=1", "lib<4"])
        self.assertEqual(str(ctx.exception), "no version of lib satisfies >=1,<4,>=3 (required by <root>, app)")

    def test_r17_no_candidate_for_a_dependency(self):
        spec = {"a": {"1.0.0": P({"x": ">=2"})}, "b": {"1.0.0": P({"x": "<2"})},
                "x": {"1.0.0": P(), "2.0.0": P()}}
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["a", "b"])
        self.assertEqual(str(ctx.exception), "no version of x satisfies >=2,<2 (required by a, b)")

    def test_r17_no_candidate_uses_the_display_name(self):
        spec = {"Foo_Bar": {"1.0.0": P()}}
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["foo-bar>=2"])
        self.assertEqual(str(ctx.exception), "no version of Foo_Bar satisfies >=2 (required by <root>)")

    def test_r17_yanked_only_package_has_no_candidate(self):
        spec = {"p": {"1.0.0": P(yanked=True)}}
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["p"])
        self.assertEqual(str(ctx.exception), "no version of p satisfies * (required by <root>)")

    def test_r17_unknown_packages(self):
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(LIB), ["nope"])
        self.assertEqual(str(ctx.exception), "unknown package nope")
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(LIB), ["Nope>=1.0"])
        self.assertEqual(str(ctx.exception), "unknown package Nope")
        spec = {"app": {"1.0.0": P({"ghost": "*"})}}
        with self.assertRaises(ResolutionError) as ctx:
            resolve(reg(spec), ["app"])
        self.assertEqual(str(ctx.exception), "unknown package ghost")

    def test_r17_parse_requirement(self):
        name, c = parse_requirement("web>=2.0")
        self.assertEqual((name, str(c)), ("web", ">=2.0"))
        name, c = parse_requirement("web")
        self.assertEqual((name, str(c)), ("web", "*"))
        name, c = parse_requirement("Foo_Bar ^1.2 , != 1.2.5")
        self.assertEqual((name, str(c)), ("Foo_Bar", "^1.2,!=1.2.5"))
        for bad in ["", "   ", ">=1.0", "web>=", "web>=1,,2"]:
            with self.subTest(text=bad):
                with self.assertRaises(ConstraintError):
                    parse_requirement(bad)

    def test_r17_random_resolutions_satisfy_every_constraint(self):
        rng = random.Random(17)
        constraint_pool = ["*", ">=1.0.0", "<3.0.0", "^1.0", "^2.0.0", "~1.1", ">=1.2.0,<2.5.0", "!=2.0.0", "<=2.0.0"]
        solved = failed = 0
        for _ in range(250):
            spec = {}
            for i in range(6):
                spec[f"p{i}"] = {
                    f"{major}.{minor}.0": P({f"p{j}": rng.choice(constraint_pool)
                                             for j in rng.sample(range(i + 1, 6), rng.randint(0, min(2, 5 - i)))},
                                            yanked=rng.random() < 0.15)
                    for major in (1, 2, 3) for minor in (0, 1, 2) if rng.random() < 0.7}
                if not spec[f"p{i}"]:
                    spec[f"p{i}"] = {"1.0.0": P()}
            registry = reg(spec)
            roots = [f"p{rng.randint(0, 2)}{rng.choice(constraint_pool[:5])}" for _ in range(rng.randint(1, 2))]
            try:
                got = resolve(registry, roots)
            except ResolutionError:
                failed += 1
                continue
            solved += 1
            chosen = {pv.name: pv for pv in got}
            self.assertEqual(len(chosen), len(got))
            wanted = [parse_requirement(r) for r in roots]
            for pv in got:
                for dep, text in pv.deps.items():
                    wanted.append((dep, Constraint(text)))
                    self.assertIn(dep, chosen)
            for name, c in wanted:
                self.assertTrue(c.matches(chosen[name].version), (roots, name, str(c)))
            for pv in got:
                if pv.yanked:
                    self.assertTrue(any(c.pins(pv.version) for n, c in wanted if n == pv.name))
        self.assertGreater(solved, 50)
        self.assertGreater(failed, 5)


# ---------------------------------------------------------------------------------------------------------
# Planning (R18-R20)
# ---------------------------------------------------------------------------------------------------------

class HiddenPlan(Case):
    def test_r18_actions(self):
        spec = {
            "web": {"1.0.0": P(size=10), "2.0.0": P(size=20)},
            "db": {"2.0.0": P(size=30), "3.0.0": P(size=40)},
            "core": {"1.0.0": P(size=50)},
            "lib": {"1.0.0": P(size=60)},
            "new": {"1.0.0": P(size=70, yanked=False)},
        }
        installed = {"WEB": "1.0.0", "db": "3.0.0", "core": "1.0.0", "lib": "1.0.0+local", "other": "9.9.9"}
        steps = plan(spec, ["web", "db<3", "core", "lib", "new"], installed, upgrade_all=True)
        got = {s.name: (str(s.version), s.action, s.size) for s in steps}
        self.assertEqual(got, {"web": ("2.0.0", "upgrade", 20), "db": ("2.0.0", "downgrade", 30),
                               "core": ("1.0.0", "keep", 50), "lib": ("1.0.0", "keep", 60),
                               "new": ("1.0.0", "install", 70)})

    def test_r18_everything_is_an_install_without_an_installed_set(self):
        steps = plan({"a": {"1.0.0": P()}, "b": {"1.0.0": P()}}, ["a", "b"])
        self.assertEqual([s.action for s in steps], ["install", "install"])

    def test_r18_installed_packages_outside_the_plan_are_not_listed(self):
        steps = plan({"a": {"1.0.0": P()}}, ["a"], {"zzz": "1.0.0", "a": "1.0.0"})
        self.assertEqual([s.name for s in steps], ["a"])

    def test_r18_step_carries_yanked_flag(self):
        steps = plan({"a": {"1.0.0": P(yanked=True)}, "b": {"1.0.0": P()}}, ["a==1.0.0", "b"])
        self.assertEqual({s.name: s.yanked for s in steps}, {"a": True, "b": False})

    def test_r19_dependencies_come_first(self):
        spec = {"app": {"1.0.0": P({"web": "*", "core": "*"})}, "web": {"1.0.0": P({"core": "*"})},
                "core": {"1.0.0": P()}}
        self.assertEqual([s.name for s in plan(spec, ["app"])], ["core", "web", "app"])

    def test_r19_smallest_ready_package_goes_next(self):
        spec = {"m": {"1.0.0": P()}, "z": {"1.0.0": P()}, "a": {"1.0.0": P({"m": "*"})}}
        # m is ready first; once it is placed, a (smaller than z) becomes ready and goes before z
        self.assertEqual([s.name for s in plan(spec, ["z", "a"])], ["m", "a", "z"])

    def test_r19_ties_use_lookup_keys_not_raw_names(self):
        spec = {"Zlib": {"1.0.0": P()}, "apple": {"1.0.0": P()}, "Mid_Pkg": {"1.0.0": P()}}
        self.assertEqual([s.name for s in plan(spec, ["Zlib", "apple", "mid-pkg"])], ["apple", "Mid_Pkg", "Zlib"])

    def test_r19_independent_of_resolution_order(self):
        spec = {"c": {"1.0.0": P()}, "b": {"1.0.0": P()}, "a": {"1.0.0": P()}}
        self.assertEqual([s.name for s in plan(spec, ["c", "b", "a"])], ["a", "b", "c"])
        self.assertEqual([s.name for s in plan(spec, ["a", "c", "b"])], ["a", "b", "c"])

    def test_r19_a_package_depending_on_itself_is_fine(self):
        spec = {"s": {"1.0.0": P({"s": "*"})}, "t": {"1.0.0": P({"s": "*"})}}
        self.assertEqual([s.name for s in plan(spec, ["t", "s"])], ["s", "t"])

    def test_r19_dependency_spelling_does_not_matter(self):
        spec = {"Core_Lib": {"1.0.0": P()}, "app": {"1.0.0": P({"core.lib": "*"})}, "aaa": {"1.0.0": P()}}
        self.assertEqual([s.name for s in plan(spec, ["app", "aaa"])], ["aaa", "Core_Lib", "app"])

    def test_r20_cycle_is_an_error(self):
        spec = {"a": {"1.0.0": P({"b": "*"})}, "b": {"1.0.0": P({"a": "*"})}, "c": {"1.0.0": P({"a": "*"})},
                "d": {"1.0.0": P()}}
        resolved = resolve(reg(spec), ["a", "d", "c"])
        with self.assertRaises(ResolutionError) as ctx:
            build_plan(resolved)
        self.assertEqual(str(ctx.exception), "dependency cycle among: a, b, c")

    def test_r20_cycle_message_sorts_by_lookup_key_and_uses_display_names(self):
        spec = {"Zed": {"1.0.0": P({"alpha": "*"})}, "alpha": {"1.0.0": P({"Zed": "*"})}}
        with self.assertRaises(ResolutionError) as ctx:
            build_plan(resolve(reg(spec), ["Zed"]))
        self.assertEqual(str(ctx.exception), "dependency cycle among: alpha, Zed")

    def test_r19_r20_random_plans_are_topological(self):
        rng = random.Random(1920)
        built = cyc = 0
        for _ in range(200):
            spec = {}
            for i in range(7):
                deps = {f"n{j}": "*" for j in rng.sample(range(7), rng.randint(0, 2))}
                spec[f"n{i}"] = {"1.0.0": P(deps)}
            roots = [f"n{rng.randint(0, 6)}" for _ in range(rng.randint(1, 3))]
            resolved = resolve(reg(spec), roots)
            try:
                steps = build_plan(resolved)
            except ResolutionError as exc:
                self.assertTrue(str(exc).startswith("dependency cycle among: "))
                cyc += 1
                continue
            built += 1
            position = {s.name: i for i, s in enumerate(steps)}
            self.assertEqual(sorted(position), sorted(pv.name for pv in resolved))
            for pv in resolved:
                for dep in pv.deps:
                    if dep != pv.name:
                        self.assertLess(position[dep], position[pv.name])
            # among ready packages the smallest key goes next: re-simulate
            done, order = set(), []
            remaining = {pv.name: {d for d in pv.deps if d != pv.name} for pv in resolved}
            while remaining:
                ready = sorted(n for n, d in remaining.items() if d <= done)
                order.append(ready[0])
                done.add(ready[0])
                del remaining[ready[0]]
            self.assertEqual([s.name for s in steps], order)
        self.assertGreater(built, 20)
        self.assertGreater(cyc, 5)


# ---------------------------------------------------------------------------------------------------------
# Report (R21-R24)
# ---------------------------------------------------------------------------------------------------------

class HiddenReport(Case):
    def test_r21_bytes_below_one_kib(self):
        for n, want in [(0, "0 B"), (1, "1 B"), (512, "512 B"), (1023, "1023 B")]:
            self.assertEqual(format_size(n), want)

    def test_r21_kib_with_one_decimal(self):
        for n, want in [(1024, "1.0 KiB"), (1025, "1.0 KiB"), (1075, "1.0 KiB"), (1127, "1.1 KiB"),
                        (1229, "1.2 KiB"), (1331, "1.3 KiB"), (1536, "1.5 KiB"), (10240, "10.0 KiB"),
                        (1177, "1.1 KiB"), (1178, "1.2 KiB")]:
            with self.subTest(n=n):
                self.assertEqual(format_size(n), want)

    def test_r21_rounds_half_up(self):
        for n, want in [(1280, "1.3 KiB"), (2304, "2.3 KiB"), (1792, "1.8 KiB"), (1310720, "1.3 MiB"),
                        (2359296, "2.3 MiB"), (1024 * 1024 * 1024 * 5 // 4, "1.3 GiB")]:
            with self.subTest(n=n):
                self.assertEqual(format_size(n), want)

    def test_r21_rounding_up_to_1024_moves_to_the_next_unit(self):
        self.assertEqual(format_size(1048524), "1023.9 KiB")
        self.assertEqual(format_size(1048525), "1.0 MiB")
        self.assertEqual(format_size(1048575), "1.0 MiB")
        self.assertEqual(format_size(1048576), "1.0 MiB")
        self.assertEqual(format_size(1073741823), "1.0 GiB")
        self.assertEqual(format_size(1073741824), "1.0 GiB")

    def test_r21_mib_and_gib(self):
        self.assertEqual(format_size(1572864), "1.5 MiB")
        self.assertEqual(format_size(5 * 1024 ** 2), "5.0 MiB")
        self.assertEqual(format_size(5 * 1024 ** 3 + 1024 ** 3 // 2), "5.5 GiB")

    def test_r21_gib_is_the_largest_unit(self):
        self.assertEqual(format_size(1024 ** 4), "1024.0 GiB")
        self.assertEqual(format_size(10 * 1024 ** 4), "10240.0 GiB")

    def test_r21_negative_sizes_are_rejected(self):
        with self.assertRaises(ValueError):
            format_size(-1)

    def test_r21_random_sizes_match_an_exact_model(self):
        rng = random.Random(21)

        def model(n):
            if n < 1024:
                return f"{n} B"
            unit = 1
            while unit < 3 and n >= 1024 ** (unit + 1):
                unit += 1

            def tenths(u):
                x = Fraction(n, 1024 ** u) * 10
                return int(x) + (1 if x - int(x) >= Fraction(1, 2) else 0)

            t = tenths(unit)
            if t >= 10240 and unit < 3:
                unit += 1
                t = tenths(unit)
            return f"{t // 10}.{t % 10} {('B', 'KiB', 'MiB', 'GiB')[unit]}"

        samples = [rng.randint(0, 5000) for _ in range(300)]
        samples += [rng.randint(1000000, 1100000) for _ in range(300)]
        samples += [rng.randint(1073000000, 1074000000) for _ in range(200)]
        samples += [rng.randint(0, 10 ** 12) for _ in range(200)]
        samples += [1024 * k + 512 for k in range(0, 400, 7)] + [1024 ** 2 * k * 5 // 4 for k in range(1, 50)]
        for n in samples:
            with self.subTest(n=n):
                self.assertEqual(format_size(n), model(n))

    def test_r22_report_layout(self):
        spec = {
            "core": {"1.4.0": P(size=2048)},
            "Net": {"2.0.0": P({"core": "*"}, size=1280)},
            "app": {"0.3.0": P({"Net": "*", "core": "*"}, size=5)},
        }
        got = report(spec, ["app"], installed={"core": "1.4.0"})
        want = (
            "Plan: 2 install, 0 upgrade, 0 downgrade, 1 keep\n"
            "1. core 1.4.0 keep            -\n"
            "2. Net  2.0.0 install   1.3 KiB\n"
            "3. app  0.3.0 install       5 B\n"
            "Total download: 1.3 KiB\n"
        )
        self.assertEqual(got, want)

    def test_r22_counts_and_actions(self):
        spec = {
            "a": {"1.0.0": P(size=100)}, "b": {"1.0.0": P(size=200), "2.0.0": P(size=300)},
            "c": {"1.0.0": P(size=400), "2.0.0": P(size=500)}, "d": {"1.0.0": P(size=600)},
            "e": {"1.0.0": P(size=700)},
        }
        installed = {"b": "1.0.0", "c": "2.0.0", "d": "1.0.0"}
        got = report(spec, ["a", "b", "c<2", "d", "e"], installed, upgrade=["b"])
        want = (
            "Plan: 2 install, 1 upgrade, 1 downgrade, 1 keep\n"
            "1. a 1.0.0 install   100 B\n"
            "2. b 2.0.0 upgrade   300 B\n"
            "3. c 1.0.0 downgrade 400 B\n"
            "4. d 1.0.0 keep          -\n"
            "5. e 1.0.0 install   700 B\n"
            "Total download: 1.5 KiB\n"
        )
        self.assertEqual(got, want)

    def test_r22_total_excludes_kept_packages(self):
        spec = {"a": {"1.0.0": P(size=1000000)}, "b": {"1.0.0": P(size=100)}}
        got = report(spec, ["a", "b"], {"a": "1.0.0"})
        self.assertTrue(got.endswith("Total download: 100 B\n"), got)

    def test_r22_index_column_is_right_aligned(self):
        spec = {f"p{i:02d}": {"1.0.0": P(size=i)} for i in range(1, 11)}
        lines = report(spec, [f"p{i:02d}" for i in range(1, 11)]).splitlines()
        self.assertEqual(lines[0], "Plan: 10 install, 0 upgrade, 0 downgrade, 0 keep")
        self.assertEqual(lines[1], " 1. p01 1.0.0 install    1 B")
        self.assertEqual(lines[9], " 9. p09 1.0.0 install    9 B")
        self.assertEqual(lines[10], "10. p10 1.0.0 install   10 B")
        self.assertEqual(lines[11], "Total download: 55 B")

    def test_r22_columns_widen_to_the_longest_value(self):
        spec = {"tiny": {"1.0.0-rc.1+b": P(size=0)}, "a-much-longer-name": {"10.20.30": P(size=1536)}}
        got = report(spec, ["tiny==1.0.0-rc.1+b", "a-much-longer-name"])
        want = (
            "Plan: 2 install, 0 upgrade, 0 downgrade, 0 keep\n"
            "1. a-much-longer-name 10.20.30     install   1.5 KiB\n"
            "2. tiny               1.0.0-rc.1+b install       0 B\n"
            "Total download: 1.5 KiB\n"
        )
        self.assertEqual(got, want)

    def test_r22_size_column_keeps_dash_for_kept_rows_aligned(self):
        spec = {"a": {"1.0.0": P(size=3 * 1024 * 1024)}, "b": {"1.0.0": P(size=1)}}
        got = report(spec, ["a", "b"], {"b": "1.0.0"})
        want = (
            "Plan: 1 install, 0 upgrade, 0 downgrade, 1 keep\n"
            "1. a 1.0.0 install   3.0 MiB\n"
            "2. b 1.0.0 keep            -\n"
            "Total download: 3.0 MiB\n"
        )
        self.assertEqual(got, want)

    def test_r22_zero_total(self):
        got = report({"a": {"1.0.0": P(size=0)}}, ["a"])
        self.assertEqual(got, "Plan: 1 install, 0 upgrade, 0 downgrade, 0 keep\n"
                              "1. a 1.0.0 install   0 B\n"
                              "Total download: 0 B\n")

    def test_r23_nothing_to_do(self):
        spec = {"a": {"1.0.0": P(size=5)}, "b": {"2.0.0": P(size=5)}}
        self.assertEqual(report(spec, ["a", "b"], {"a": "1.0.0", "b": "2.0.0"}), "Nothing to do.\n")
        self.assertEqual(format_report([]), "Nothing to do.\n")

    def test_r23_a_single_change_is_not_nothing_to_do(self):
        spec = {"a": {"1.0.0": P(size=5)}, "b": {"2.0.0": P(size=5)}}
        got = report(spec, ["a", "b"], {"a": "1.0.0"})
        self.assertTrue(got.startswith("Plan: 1 install"), got)

    def test_r24_yanked_warnings(self):
        spec = {
            "zed": {"1.0.0+b": P(size=1, yanked=True)},
            "Alpha": {"2.0.0": P({"zed": "==1.0.0"}, size=1, yanked=True)},
            "ok": {"1.0.0": P(size=1)},
        }
        got = report(spec, ["Alpha==2.0.0", "ok"])
        want = (
            "Plan: 3 install, 0 upgrade, 0 downgrade, 0 keep\n"
            "1. ok    1.0.0   install   1 B\n"
            "2. zed   1.0.0+b install   1 B\n"
            "3. Alpha 2.0.0   install   1 B\n"
            "Total download: 3 B\n"
            "warning: Alpha 2.0.0 is yanked\n"
            "warning: zed 1.0.0+b is yanked\n"
        )
        self.assertEqual(got, want)

    def test_r24_installed_yanked_version_also_warns(self):
        spec = {"a": {"1.0.0": P(size=1, yanked=True), "2.0.0": P(size=1)}, "b": {"1.0.0": P(size=9)}}
        got = report(spec, ["a", "b"], {"a": "1.0.0"})
        self.assertTrue(got.endswith("Total download: 9 B\nwarning: a 1.0.0 is yanked\n"), got)

    def test_r24_warning_follows_nothing_to_do(self):
        spec = {"a": {"1.0.0": P(size=1, yanked=True)}}
        self.assertEqual(report(spec, ["a"], {"a": "1.0.0"}), "Nothing to do.\nwarning: a 1.0.0 is yanked\n")


# ---------------------------------------------------------------------------------------------------------
# Lock files (R25, R26)
# ---------------------------------------------------------------------------------------------------------

class HiddenLock(Case):
    def test_r25_dump_lock(self):
        spec = {"zeta": {"1.0.0": P()}, "alpha": {"1.2.3-rc.1": P()}, "Mid_Pkg": {"2.0.0+b1": P()}}
        steps = plan(spec, ["zeta", "alpha>=1.0.0-0", "Mid_Pkg"])
        self.assertEqual(dump_lock(steps), "# pkgplan lock v1\nalpha==1.2.3-rc.1\nMid_Pkg==2.0.0+b1\nzeta==1.0.0\n")

    def test_r25_dump_lock_is_sorted_by_key_not_by_plan_order(self):
        spec = {"app": {"1.0.0": P({"Zlib": "*", "lib": "*"})}, "lib": {"1.0.0": P()}, "Zlib": {"2.0.0": P()}}
        steps = plan(spec, ["app"])
        self.assertEqual([s.name for s in steps], ["lib", "Zlib", "app"])
        self.assertEqual(dump_lock(steps), "# pkgplan lock v1\napp==1.0.0\nlib==1.0.0\nZlib==2.0.0\n")

    def test_r25_dump_lock_includes_kept_packages_and_empty_plans(self):
        spec = {"a": {"1.0.0": P()}, "B": {"1.0.0": P()}}
        steps = plan(spec, ["a", "B"], {"a": "1.0.0"})
        self.assertEqual(dump_lock(steps), "# pkgplan lock v1\na==1.0.0\nB==1.0.0\n")
        self.assertEqual(dump_lock([]), "# pkgplan lock v1\n")

    def test_r26_load_lock(self):
        text = "# pkgplan lock v1\n\n  Foo_Bar == 1.0.0 \nweb==2.1.0-rc.1+x\n   # note\n"
        got = load_lock(text)
        self.assertEqual(got, {"foo-bar": v("1.0.0"), "web": v("2.1.0-rc.1")})
        self.assertEqual(str(got["web"]), "2.1.0-rc.1+x")

    def test_r26_load_lock_errors(self):
        with self.assertRaises(LockError) as ctx:
            load_lock("# c\nweb 1.0.0\n")
        self.assertEqual(str(ctx.exception), "line 2: expected name==version")
        with self.assertRaises(LockError) as ctx:
            load_lock("a==1.0.0\n\n==2.0.0\n")
        self.assertEqual(str(ctx.exception), "line 3: expected name==version")
        with self.assertRaises(LockError) as ctx:
            load_lock("Foo_Bar==1.0.0\nfoo-bar==1.0.0\n")
        self.assertEqual(str(ctx.exception), "line 2: duplicate package foo-bar")
        self.assertTrue(issubclass(LockError, ValueError))

    def test_r26_load_lock_rejects_bad_versions(self):
        with self.assertRaises(VersionError):
            load_lock("a==1.0\n")

    def test_r25_r26_round_trip_feeds_the_next_plan(self):
        spec = {"app": {"1.0.0": P({"lib": "*"}, size=5)}, "lib": {"1.0.0": P(size=7), "2.0.0": P(size=9)}}
        first = plan(spec, ["app"])
        locked = load_lock(dump_lock(first))
        self.assertEqual({k: str(x) for k, x in locked.items()}, {"app": "1.0.0", "lib": "2.0.0"})
        again = plan(spec, ["app"], locked)
        self.assertTrue(all(s.action == "keep" for s in again))
        self.assertEqual(format_report(again), "Nothing to do.\n")


# ---------------------------------------------------------------------------------------------------------
# Command line (R27, R28)
# ---------------------------------------------------------------------------------------------------------

CLI_SPEC = {
    "app": {"1.0.0": P({"web": ">=1.0.0,<3", "Core_Lib": "^1"}, size=100)},
    "web": {"1.0.0": P(size=2048), "1.5.0": P({"core-lib": "*"}, size=4096, yanked=True),
            "2.0.0": P({"core.lib": "~1.1"}, size=3000), "3.0.0": P(size=1)},
    "Core_Lib": {"1.0.0": P(size=10), "1.1.0": P(size=20), "1.2.0-rc.1": P(size=30), "2.0.0": P(size=40)},
}


class HiddenCli(Case):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.registry = self.write("registry.json", json.dumps(CLI_SPEC))

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def read(self, path):
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_r27_plan_prints_the_report(self):
        code, out, err = run(["plan", "--registry", self.registry, "app"])
        self.assertEqual((code, err), (0, ""))
        want = (
            "Plan: 3 install, 0 upgrade, 0 downgrade, 0 keep\n"
            "1. Core_Lib 1.1.0 install      20 B\n"
            "2. web      2.0.0 install   2.9 KiB\n"
            "3. app      1.0.0 install     100 B\n"
            "Total download: 3.0 KiB\n"
        )
        self.assertEqual(out, want)

    def test_r27_option_order_does_not_matter(self):
        a = run(["plan", "app", "--registry", self.registry])
        b = run(["plan", "--registry", self.registry, "app"])
        self.assertEqual(a[0], 0)
        self.assertEqual(a, b)
        c = run(["plan", "--registry", self.registry, "web>=1.0.0", "Core_Lib"])
        self.assertEqual(c[0], 0)

    def test_r27_installed_lock_is_used(self):
        lock = self.write("old.lock", "# pkgplan lock v1\nweb==1.0.0\ncore-lib==1.0.0\n")
        code, out, err = run(["plan", "--registry", self.registry, "--installed", lock, "app"])
        self.assertEqual((code, err), (0, ""))
        want = (
            "Plan: 1 install, 0 upgrade, 0 downgrade, 2 keep\n"
            "1. Core_Lib 1.0.0 keep          -\n"
            "2. web      1.0.0 keep          -\n"
            "3. app      1.0.0 install   100 B\n"
            "Total download: 100 B\n"
        )
        self.assertEqual(out, want)

    def test_r27_upgrade_options(self):
        lock = self.write("old.lock", "web==1.0.0\ncore-lib==1.0.0\n")
        base = ["plan", "--registry", self.registry, "--installed", lock, "app"]
        code, out, _ = run(base + ["--upgrade", "WEB", "--upgrade", "Core.Lib"])
        self.assertEqual(code, 0)
        self.assertIn("1. Core_Lib 1.1.0 upgrade", out)
        self.assertIn("2. web      2.0.0 upgrade", out)
        code, out, _ = run(base + ["--upgrade-all"])
        self.assertIn("web      2.0.0 upgrade", out)
        # web 2.0.0 needs Core_Lib ~1.1, but Core_Lib 1.0.0 was already kept when web was reached
        code, out, err = run(base + ["--upgrade", "web"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "error: conflict on Core_Lib: 1.0.0 was chosen for ^1 but ~1.1 is required by web\n")

    def test_r27_prerelease_flag(self):
        code, out, _ = run(["plan", "--registry", self.registry, "Core_Lib<2", "--prerelease"])
        self.assertEqual(code, 0)
        self.assertIn("Core_Lib 1.2.0-rc.1 install", out)
        code, out, _ = run(["plan", "--registry", self.registry, "Core_Lib<2"])
        self.assertIn("Core_Lib 1.1.0 install", out)

    def test_r27_write_lock(self):
        target = os.path.join(self.tmp.name, "new.lock")
        code, out, err = run(["plan", "--registry", self.registry, "app", "--write-lock", target])
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.startswith("Plan: 3 install"))
        self.assertEqual(self.read(target), "# pkgplan lock v1\napp==1.0.0\nCore_Lib==1.1.0\nweb==2.0.0\n")
        code, out, err = run(["plan", "--registry", self.registry, "app", "--installed", target])
        self.assertEqual((code, out, err), (0, "Nothing to do.\n", ""))

    def test_r27_write_lock_also_after_nothing_to_do(self):
        lock = self.write("a.lock", "app==1.0.0\nweb==2.0.0\ncore_lib==1.1.0\n")
        target = os.path.join(self.tmp.name, "b.lock")
        code, out, _ = run(["plan", "--registry", self.registry, "app", "--installed", lock, "--write-lock", target])
        self.assertEqual((code, out), (0, "Nothing to do.\n"))
        self.assertEqual(self.read(target), "# pkgplan lock v1\napp==1.0.0\nCore_Lib==1.1.0\nweb==2.0.0\n")

    def test_r27_resolution_errors_exit_2(self):
        target = os.path.join(self.tmp.name, "never.lock")
        code, out, err = run(["plan", "--registry", self.registry, "web>=9", "--write-lock", target])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "error: no version of web satisfies >=9 (required by <root>)\n")
        self.assertFalse(os.path.exists(target))
        code, out, err = run(["plan", "--registry", self.registry, "nope"])
        self.assertEqual((code, out, err), (2, "", "error: unknown package nope\n"))

    def test_r27_conflict_and_cycle_errors_exit_2(self):
        spec = {"a": {"1.0.0": P({"b": "*"})}, "b": {"1.0.0": P({"a": "*"})}}
        path = self.write("cycle.json", json.dumps(spec))
        code, out, err = run(["plan", "--registry", path, "a"])
        self.assertEqual((code, out, err), (2, "", "error: dependency cycle among: a, b\n"))
        code, out, err = run(["plan", "--registry", self.registry, "web", "app"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "error: conflict on web: 3.0.0 was chosen for * but >=1.0.0,<3 is required by app\n")

    def test_r28_usage_errors_exit_64(self):
        cases = {
            "no command": [],
            "unknown command": ["frobnicate"],
            "no requirements": ["plan", "--registry", self.registry],
            "no registry": ["plan", "app"],
            "unknown option": ["plan", "--registry", self.registry, "app", "--bogus"],
            "missing value": ["plan", "app", "--registry"],
            "missing registry file": ["plan", "--registry", os.path.join(self.tmp.name, "nope.json"), "app"],
            "bad requirement": ["plan", "--registry", self.registry, "app>=1..0"],
            "missing lock file": ["plan", "--registry", self.registry, "app", "--installed",
                                  os.path.join(self.tmp.name, "nope.lock")],
        }
        for label, argv in cases.items():
            with self.subTest(case=label):
                code, out, err = run(argv)
                self.assertEqual(code, 64)
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("error: ") and err.endswith("\n") and err.count("\n") == 1, err)

    def test_r28_bad_input_files_exit_64(self):
        bad_json = self.write("bad.json", "{not json")
        bad_version = self.write("badver.json", json.dumps({"p": {"1.0": {}}}))
        bad_size = self.write("badsize.json", json.dumps({"p": {"1.0.0": {"size": -1}}}))
        bad_lock = self.write("bad.lock", "web 1.0.0\n")
        dup_lock = self.write("dup.lock", "web==1.0.0\nWEB==1.0.0\n")
        for label, argv in {
            "bad json": ["plan", "--registry", bad_json, "p"],
            "bad registry version": ["plan", "--registry", bad_version, "p"],
            "bad registry size": ["plan", "--registry", bad_size, "p"],
            "bad lock": ["plan", "--registry", self.registry, "app", "--installed", bad_lock],
            "duplicate lock entry": ["plan", "--registry", self.registry, "app", "--installed", dup_lock],
        }.items():
            with self.subTest(case=label):
                code, out, err = run(argv)
                self.assertEqual((code, out), (64, ""))
                self.assertTrue(err.startswith("error: "), err)

    def test_r29_show(self):
        code, out, err = run(["show", "--registry", self.registry, "web"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "web\n  3.0.0\n  2.0.0\n  1.5.0 (yanked)\n  1.0.0\n")
        code, out, err = run(["show", "--registry", self.registry, "app"])
        self.assertEqual(out, "app\n  1.0.0\n")

    def test_r29_show_unknown_package(self):
        code, out, err = run(["show", "--registry", self.registry, "nope"])
        self.assertEqual((code, out, err), (2, "", "error: unknown package nope\n"))
        self.assertEqual(run(["show", "--registry", self.registry])[0], 64)
        self.assertEqual(run(["show", "--registry", self.registry, "a", "b"])[0], 64)

    def test_r29_show_uses_lookup_keys_and_prints_the_display_name(self):
        code, out, err = run(["show", "--registry", self.registry, "core-lib"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "Core_Lib\n  2.0.0\n  1.2.0-rc.1\n  1.1.0\n  1.0.0\n")

    def test_r29_list(self):
        code, out, err = run(["list", "--registry", self.registry])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "app 1\nCore_Lib 4\nweb 4\n")
        self.assertEqual(run(["list", "--registry", self.registry, "extra"])[0], 64)

    def test_r29_rdeps(self):
        code, out, err = run(["rdeps", "--registry", self.registry, "Core_Lib"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "app\nweb\n")
        self.assertEqual(run(["rdeps", "--registry", self.registry, "app"]), (0, "", ""))
        self.assertEqual(run(["rdeps", "--registry", self.registry, "nope"]), (2, "", "error: unknown package nope\n"))

    def test_r29_reach(self):
        code, out, err = run(["reach", "--registry", self.registry, "app"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "Core_Lib\nweb\n")
        self.assertEqual(run(["reach", "--registry", self.registry, "web"])[1], "Core_Lib\n")
        self.assertEqual(run(["reach", "--registry", self.registry, "Core_Lib"]), (0, "", ""))
        self.assertEqual(run(["reach", "--registry", self.registry, "nope"])[0], 2)

    def test_r27_default_streams_are_used_when_none_are_passed(self):
        import contextlib
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["show", "--registry", self.registry, "app"])
        self.assertEqual((code, out.getvalue(), err.getvalue()), (0, "app\n  1.0.0\n", ""))


if __name__ == "__main__":
    unittest.main()

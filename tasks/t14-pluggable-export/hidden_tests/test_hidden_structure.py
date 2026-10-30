"""Hidden grader for t14, part 2: the new structure (R9 to R12), reached through the public
interface only. All of these fail on the starting code. Imports happen inside the tests so that
each one fails (or passes) on its own."""
import copy
import importlib
import unittest

PEOPLE = [
    {"name": "Ann", "age": 31, "score": 9.5, "ok": True},
    {"name": "Bob", "age": 25, "score": 7.0, "ok": False},
    {"name": "Cy", "age": None, "score": 8.25},
    {"name": "Di", "age": 25, "score": None, "ok": True},
]


def formats():
    return importlib.import_module("exportkit.formats")


def prepare():
    return importlib.import_module("exportkit.rows").prepare


def export():
    return importlib.import_module("exportkit").export


class Recorder:
    """A renderer that remembers how it was called."""

    def __init__(self, result="RENDERED"):
        self.calls = []
        self.result = result

    def __call__(self, columns, rows):
        self.calls.append((columns, rows))
        return self.result


class HiddenStructure(unittest.TestCase):
    def register(self, name, renderer, **kw):
        f = formats()
        f.register(name, renderer, **kw)
        self.addCleanup(lambda: name in f.names() and f.unregister(name))

    def replace_builtin(self, name, renderer):
        f = formats()
        original = f.get(name)
        f.register(name, renderer, replace=True)
        self.addCleanup(f.register, name, original, replace=True)

    # ---- R9 prepare ---------------------------------------------------------------------------------
    def test_R9_prepare_returns_columns_and_raw_rows(self):
        columns, rows = prepare()(PEOPLE)
        self.assertEqual(columns, ["name", "age", "score", "ok"])
        self.assertIsInstance(columns, list)
        self.assertEqual(rows[0], ["Ann", 31, 9.5, True])
        self.assertEqual(rows[2], ["Cy", None, 8.25, None])
        self.assertTrue(all(isinstance(row, list) for row in rows))
        self.assertIs(rows[0][3], True)

    def test_R9_prepare_selects_sorts_and_limits(self):
        columns, rows = prepare()(PEOPLE, columns=("score", "name"), sort_by="score",
                                  descending=True, limit=3)
        self.assertEqual(columns, ["score", "name"])
        self.assertEqual(rows, [[9.5, "Ann"], [8.25, "Cy"], [7.0, "Bob"]])
        columns, rows = prepare()(PEOPLE, sort_by="age")
        self.assertEqual([r[0] for r in rows], ["Bob", "Di", "Ann", "Cy"])

    def test_R9_prepare_errors_and_order(self):
        for kwargs, message in [
            (dict(columns=["a", "a"], sort_by="zz", limit=-1), "duplicate column 'a'"),
            (dict(sort_by="zz", limit=-1), "unknown sort column 'zz'"),
            (dict(limit=1.5), "limit must be a non-negative int"),
        ]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError) as cm:
                    prepare()(PEOPLE, **kwargs)
                self.assertEqual(str(cm.exception), message)

    def test_R9_prepare_empty_and_does_not_modify_records(self):
        self.assertEqual(prepare()([]), ([], []))
        self.assertEqual(prepare()([{}, {}]), ([], [[], []]))
        self.assertEqual(prepare()([], columns=["a"]), (["a"], []))
        before = copy.deepcopy(PEOPLE)
        prepare()(PEOPLE, sort_by="score", limit=2)
        self.assertEqual(PEOPLE, before)

    # ---- R10 registry ---------------------------------------------------------------------------------
    def test_R10_register_get_unregister(self):
        f = formats()
        renderer = Recorder()
        self.register("mine", renderer)
        self.assertIs(f.get("mine"), renderer)
        self.assertIn("mine", f.names())
        f.unregister("mine")
        self.assertNotIn("mine", f.names())
        with self.assertRaises(KeyError):
            f.unregister("mine")

    def test_R10_register_validation(self):
        f = formats()
        with self.assertRaises(ValueError):
            f.register("csv", Recorder())            # already registered
        for bad in ("", None, 5):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    f.register(bad, Recorder())
        with self.assertRaises(TypeError):
            f.register("notcallable", "text")
        self.assertNotIn("notcallable", f.names())

    def test_R10_replace_flag(self):
        f = formats()
        first, second = Recorder(), Recorder()
        self.register("twice", first)
        with self.assertRaises(ValueError):
            f.register("twice", second)
        self.assertIs(f.get("twice"), first)
        f.register("twice", second, replace=True)
        self.assertIs(f.get("twice"), second)

    def test_R10_names_are_sorted(self):
        f = formats()
        self.register("zzz", Recorder())
        self.register("aaa", Recorder())
        listed = f.names()
        self.assertIsInstance(listed, list)
        self.assertEqual(listed, sorted(listed))
        self.assertTrue({"aaa", "zzz"} <= set(listed))

    def test_R10_unknown_format_error(self):
        f = formats()
        pkg = importlib.import_module("exportkit")
        self.assertTrue(issubclass(pkg.UnknownFormatError, ValueError))
        with self.assertRaises(pkg.UnknownFormatError) as cm:
            f.get("xml")
        self.assertEqual(str(cm.exception), "unknown format 'xml'")
        with self.assertRaises(pkg.UnknownFormatError):
            export()(PEOPLE, "xml")

    # ---- R11 built-ins -----------------------------------------------------------------------------------
    def test_R11_builtins_are_registered(self):
        f = formats()
        self.assertTrue({"csv", "json", "table"} <= set(f.names()))
        for name in ("csv", "json", "table"):
            self.assertTrue(callable(f.get(name)))

    def test_R11_builtin_renderers_match_export(self):
        f, p, e = formats(), prepare(), export()
        samples = [
            (PEOPLE, {}),
            (PEOPLE, dict(columns=["ok", "name", "score"], sort_by="score", descending=True)),
            (PEOPLE, dict(sort_by="age", limit=3)),
            ([], {}),
            ([], dict(columns=["a", "b"])),
            ([{}, {}], {}),
            ([{"t": 'x,"y"', "n": 1.0}, {"t": " z", "n": None}], dict(sort_by="n")),
        ]
        for records, kwargs in samples:
            for name in ("csv", "json", "table"):
                with self.subTest(name=name, kwargs=kwargs, n=len(records)):
                    self.assertEqual(f.get(name)(*p(records, **kwargs)),
                                     e(records, name, **kwargs))

    # ---- R12 export wiring ----------------------------------------------------------------------------------
    def test_R12_custom_format_gets_prepared_columns_and_rows(self):
        recorder = Recorder("custom output")
        self.register("md", recorder)
        out = export()(PEOPLE, "md", columns=["name", "score"], sort_by="score", limit=2)
        self.assertEqual(out, "custom output")
        self.assertEqual(len(recorder.calls), 1)
        self.assertEqual(recorder.calls[0],
                         prepare()(PEOPLE, columns=["name", "score"], sort_by="score", limit=2))
        self.assertEqual(recorder.calls[0], (["name", "score"], [["Bob", 7.0], ["Cy", 8.25]]))

    def test_R12_renderer_result_is_returned_unchanged(self):
        for text in ("", "  padded \n", "unicode é\r\n"):
            with self.subTest(text=text):
                self.register("raw", Recorder(text), replace=True)
                self.assertEqual(export()(PEOPLE, "raw"), text)

    def test_R12_no_columns_still_reaches_the_renderer(self):
        recorder = Recorder("none")
        self.register("nil", recorder)
        self.assertEqual(export()([], "nil"), "none")
        self.assertEqual(recorder.calls, [([], [])])

    def test_R12_a_replaced_builtin_is_used_at_once(self):
        recorder = Recorder("mine")
        self.replace_builtin("csv", recorder)
        self.assertEqual(export()(PEOPLE, "csv", limit=1), "mine")
        self.assertEqual(len(recorder.calls), 1)
        # the other built-ins are untouched
        self.assertTrue(export()(PEOPLE, "json").startswith("["))

    def test_R12_lookup_happens_on_every_call(self):
        e = export()
        with self.assertRaises(ValueError):
            e(PEOPLE, "later")
        self.register("later", Recorder("now known"))
        self.assertEqual(e(PEOPLE, "later"), "now known")
        formats().unregister("later")
        with self.assertRaises(ValueError):
            e(PEOPLE, "later")

    def test_R12_format_is_looked_up_before_the_data_is_checked(self):
        pkg = importlib.import_module("exportkit")
        recorder = Recorder()
        self.register("quiet", recorder)
        with self.assertRaises(pkg.UnknownFormatError):
            export()(PEOPLE, "missing", columns=["a", "a"], sort_by="zz", limit=-1)
        with self.assertRaises(ValueError) as cm:
            export()(PEOPLE, "quiet", limit=-1)
        self.assertEqual(str(cm.exception), "limit must be a non-negative int")
        self.assertEqual(recorder.calls, [])  # the renderer is not called when the data is bad


if __name__ == "__main__":
    unittest.main()

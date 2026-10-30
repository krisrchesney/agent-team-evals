"""Hidden grader for t14, part 1: behaviour that must not change (R1 to R8). All of these pass on
the starting code. The last test compares against a verbatim copy of the original function on
random inputs drawn from the domain the prompt describes."""
import copy
import json
import random
import unittest

from exportkit import export

PEOPLE = [
    {"name": "Ann", "age": 31, "score": 9.5, "ok": True},
    {"name": "Bob", "age": 25, "score": 7.0, "ok": False},
    {"name": "Cy", "age": None, "score": 8.25},
    {"name": "Di", "age": 25, "score": None, "ok": True},
]


def names_of(text):
    """Row names from CSV output (first cell of each line after the header)."""
    return [line.split(",")[0] for line in text.splitlines()[1:]]


class HiddenBehaviour(unittest.TestCase):
    # ---- R1 ---------------------------------------------------------------------------------
    def test_R1_unknown_format_message(self):
        with self.assertRaises(ValueError) as cm:
            export(PEOPLE, "xml")
        self.assertEqual(str(cm.exception), "unknown format 'xml'")
        with self.assertRaises(ValueError) as cm:
            export(PEOPLE, None)
        self.assertEqual(str(cm.exception), "unknown format None")

    def test_R1_error_order_format_columns_sort_limit(self):
        def message(**kw):
            with self.assertRaises(ValueError) as cm:
                export(PEOPLE, **kw)
            return str(cm.exception)

        bad = dict(columns=["a", "a"], sort_by="zz", limit=-1)
        self.assertEqual(message(fmt="xml", **bad), "unknown format 'xml'")
        self.assertEqual(message(fmt="csv", **bad), "duplicate column 'a'")
        self.assertEqual(message(fmt="csv", sort_by="zz", limit=-1), "unknown sort column 'zz'")
        self.assertEqual(message(fmt="csv", limit=-1), "limit must be a non-negative int")

    def test_R1_returns_str_and_leaves_records_alone(self):
        before = copy.deepcopy(PEOPLE)
        for fmt in ("csv", "json", "table"):
            out = export(PEOPLE, fmt, sort_by="age", descending=True, limit=3)
            self.assertIsInstance(out, str)
        self.assertEqual(PEOPLE, before)

    # ---- R2 columns -----------------------------------------------------------------------------
    def test_R2_default_columns_are_first_seen_keys(self):
        records = [{"b": 1, "a": 2}, {"c": 3, "a": 4}, {"d": 5, "b": 6}]
        self.assertEqual(export(records, "csv"), "b,a,c,d\n1,2,,\n,4,3,\n6,,,5\n")

    def test_R2_explicit_columns_in_given_order_with_missing_as_none(self):
        out = export(PEOPLE, "json", columns=["ok", "name"], limit=3)
        self.assertEqual(json.loads(out), [{"ok": True, "name": "Ann"},
                                           {"ok": False, "name": "Bob"},
                                           {"ok": None, "name": "Cy"}])
        self.assertEqual(list(json.loads(out)[0]), ["ok", "name"])
        self.assertEqual(export(PEOPLE, "csv", columns=iter(["name", "nope"]), limit=1),
                         "name,nope\nAnn,\n")

    def test_R2_duplicate_columns(self):
        with self.assertRaises(ValueError) as cm:
            export(PEOPLE, "csv", columns=["name", "age", "name", "age"])
        self.assertEqual(str(cm.exception), "duplicate column 'name'")

    # ---- R3 sorting -----------------------------------------------------------------------------------
    def test_R3_ascending_with_none_last(self):
        self.assertEqual(names_of(export(PEOPLE, "csv", sort_by="age")), ["Bob", "Di", "Ann", "Cy"])
        self.assertEqual(names_of(export(PEOPLE, "csv", sort_by="score")), ["Bob", "Cy", "Ann", "Di"])

    def test_R3_descending_keeps_none_last_and_ties_stable(self):
        self.assertEqual(names_of(export(PEOPLE, "csv", sort_by="age", descending=True)),
                         ["Ann", "Bob", "Di", "Cy"])
        self.assertEqual(names_of(export(PEOPLE, "csv", sort_by="score", descending=True)),
                         ["Ann", "Cy", "Bob", "Di"])
        records = [{"n": "p", "k": None}, {"n": "q", "k": 1}, {"n": "r", "k": None},
                   {"n": "s", "k": 1}, {"n": "t", "k": 2}]
        self.assertEqual(names_of(export(records, "csv", sort_by="k")), ["q", "s", "t", "p", "r"])
        self.assertEqual(names_of(export(records, "csv", sort_by="k", descending=True)),
                         ["t", "q", "s", "p", "r"])

    def test_R3_numbers_before_strings_and_bool_is_a_number(self):
        records = [{"n": "a", "v": "10"}, {"n": "b", "v": 9}, {"n": "c", "v": "9"},
                   {"n": "d", "v": True}, {"n": "e", "v": 2.5}, {"n": "f", "v": 0}]
        self.assertEqual(names_of(export(records, "csv", sort_by="v")),
                         ["f", "d", "e", "b", "a", "c"])  # 0, True, 2.5, 9, "10", "9"
        self.assertEqual(names_of(export(records, "csv", sort_by="v", descending=True)),
                         ["c", "a", "b", "e", "d", "f"])

    def test_R3_other_values_compare_as_text(self):
        records = [{"n": "a", "v": (2, 1)}, {"n": "b", "v": "(1, 5)"}, {"n": "c", "v": [0]}]
        self.assertEqual(names_of(export(records, "csv", sort_by="v")), ["b", "a", "c"])  # "(1, 5)", "(2, 1)", "[0]"

    def test_R3_sort_column_must_be_a_chosen_column(self):
        with self.assertRaises(ValueError) as cm:
            export(PEOPLE, "csv", sort_by="height")
        self.assertEqual(str(cm.exception), "unknown sort column 'height'")
        with self.assertRaises(ValueError) as cm:
            export(PEOPLE, "csv", columns=["name"], sort_by="age")
        self.assertEqual(str(cm.exception), "unknown sort column 'age'")

    # ---- R4 limit ---------------------------------------------------------------------------------------------
    def test_R4_limit_applies_after_sorting(self):
        self.assertEqual(names_of(export(PEOPLE, "csv", sort_by="score", limit=2)), ["Bob", "Cy"])
        self.assertEqual(names_of(export(PEOPLE, "csv", sort_by="score", descending=True, limit=1)),
                         ["Ann"])
        self.assertEqual(len(names_of(export(PEOPLE, "csv", limit=99))), 4)
        self.assertEqual(export(PEOPLE, "csv", columns=["name"], limit=0), "name\n")

    def test_R4_invalid_limits(self):
        for bad in (-1, 1.5, "2", True, False):
            with self.subTest(limit=bad):
                with self.assertRaises(ValueError) as cm:
                    export(PEOPLE, "csv", limit=bad)
                self.assertEqual(str(cm.exception), "limit must be a non-negative int")

    # ---- R5 CSV ----------------------------------------------------------------------------------------------------
    def test_R5_cell_text(self):
        records = [{"a": None, "b": True, "c": False, "d": 3.14159, "e": 10.0, "f": 2.5, "g": 7,
                    "h": 100.0, "i": 0.0, "j": -1.5}]
        self.assertEqual(export(records, "csv"),
                         "a,b,c,d,e,f,g,h,i,j\n,true,false,3.14,10,2.5,7,100,0,-1.5\n")

    def test_R5_quoting(self):
        records = [{"a": "x,y", "b": 'say "hi"', "c": "two\nlines", "d": " lead", "e": "trail ",
                    "f": "tab\there", "g": "a\rb", "h": "plain", "i": "in side"}]
        self.assertEqual(
            export(records, "csv"),
            'a,b,c,d,e,f,g,h,i\n'
            '"x,y","say ""hi""","two\nlines"," lead","trail ",tab\there,"a\rb",plain,in side\n')

    def test_R5_header_follows_the_same_rules(self):
        records = [{"first name": 1, "a,b": 2, " pad": 3, 'q"q': 4}]
        self.assertEqual(export(records, "csv"), 'first name,"a,b"," pad","q""q"\n1,2,3,4\n')

    # ---- R6 JSON ----------------------------------------------------------------------------------------------------------
    def test_R6_json_text(self):
        records = [{"n": "é", "x": 3.14159, "y": None, "z": False}, {"n": "b", "x": 2.0, "y": 1}]
        want = ('[\n  {\n    "n": "é",\n    "x": 3.14159,\n    "y": null,\n    "z": false\n  },\n'
                '  {\n    "n": "b",\n    "x": 2.0,\n    "y": 1,\n    "z": null\n  }\n]')
        self.assertEqual(export(records, "json"), want)

    # ---- R7 table ---------------------------------------------------------------------------------------------------------------
    def test_R7_table_layout(self):
        out = export(PEOPLE, "table")
        self.assertEqual(out, "name  age  score  ok\n"
                              "----  ---  -----  ---\n"
                              "Ann    31   9.50  yes\n"
                              "Bob    25   7.00  no\n"
                              "Cy      -   8.25  -\n"
                              "Di     25      -  yes")

    def test_R7_alignment_rules(self):
        records = [{"t": "left", "n": 5, "b": True, "m": 1, "e": None},
                   {"t": "x", "n": 1234, "b": False, "m": "z", "e": None}]
        out = export(records, "table")
        self.assertEqual(out, "t        n  b    m  e\n"
                              "----  ----  ---  -  -\n"
                              "left     5  yes  1  -\n"
                              "x     1234  no   z  -")

    def test_R7_header_aligned_like_its_column_and_trailing_space_stripped(self):
        records = [{"id": 7, "label": "a"}, {"id": 12345, "label": "b"}]
        out = export(records, "table")
        self.assertEqual(out, "   id  label\n"
                              "-----  -----\n"
                              "    7  a\n"
                              "12345  b")
        for line in out.splitlines():
            self.assertEqual(line, line.rstrip())

    def test_R7_floats_two_decimals_and_int_float_mix_is_numeric(self):
        records = [{"v": 3.0}, {"v": 12}, {"v": None}, {"v": 0.456}]
        self.assertEqual(export(records, "table"), "   v\n----\n3.00\n  12\n   -\n0.46")

    # ---- R8 empty input ------------------------------------------------------------------------------------------------------------------
    def test_R8_no_columns(self):
        self.assertEqual(export([], "csv"), "")
        self.assertEqual(export([], "json"), "[]")
        self.assertEqual(export([], "table"), "(no data)")
        self.assertEqual(export([{}, {}], "csv"), "")
        self.assertEqual(export([{}, {}], "json"), "[\n  {},\n  {}\n]")
        self.assertEqual(export([{}, {}], "table"), "(no data)")
        self.assertEqual(export(PEOPLE, "csv", columns=[]), "")
        self.assertEqual(export(PEOPLE, "table", columns=[]), "(no data)")

    def test_R8_columns_but_no_rows(self):
        self.assertEqual(export([], "csv", columns=["a", "b"]), "a,b\n")
        self.assertEqual(export([], "json", columns=["a", "b"]), "[]")
        self.assertEqual(export([], "table", columns=["a", "bb"]), "a  bb\n-  --")
        self.assertEqual(export(PEOPLE, "table", columns=["name"], limit=0), "name\n----")

    # ---- everything at once ---------------------------------------------------------------------------------------------------------------------
    def test_R1_to_R8_random_inputs_match_the_original_function(self):
        rng = random.Random(14)
        strings = ["", "a", "B", "x,y", 'q"r', "line\nbreak", " pad", "pad ", "10", "9", "é", "a b"]
        floats = [0.0, 1.5, -2.25, 3.14159, 10.0, 99.99, 0.07, 100.0, 2.71828, -0.5]
        values = [None, True, False, 0, 1, 7, -3, 1000] + floats + strings
        keys = ["a", "b", "c", "d", "e"]
        for _ in range(300):
            records = [{k: rng.choice(values) for k in rng.sample(keys, rng.randint(0, 5))}
                       for _ in range(rng.randint(0, 7))]
            kwargs = {}
            if rng.random() < 0.5:
                kwargs["columns"] = rng.sample(keys, rng.randint(0, 5))
            if rng.random() < 0.6:
                kwargs["sort_by"] = rng.choice(keys)
                kwargs["descending"] = rng.random() < 0.5
            if rng.random() < 0.4:
                kwargs["limit"] = rng.randint(0, 8)
            for fmt in ("csv", "json", "table"):
                snapshot = copy.deepcopy(records)
                try:
                    want = ("ok", original_export(records, fmt, **kwargs))
                except ValueError as exc:
                    want = ("error", str(exc))
                try:
                    got = ("ok", export(records, fmt, **kwargs))
                except ValueError as exc:
                    got = ("error", str(exc))
                self.assertEqual(got, want, (records, fmt, kwargs))
                self.assertEqual(records, snapshot)


def original_export(records, fmt, columns=None, sort_by=None, descending=False, limit=None):
    """The function as it was before the refactor, verbatim (the oracle for the test above)."""
    if fmt not in ("csv", "json", "table"):
        raise ValueError("unknown format %r" % (fmt,))
    if columns is None:
        cols = []
        for rec in records:
            for key in rec:
                if key not in cols:
                    cols.append(key)
    else:
        cols = list(columns)
        seen = set()
        for c in cols:
            if c in seen:
                raise ValueError("duplicate column %r" % (c,))
            seen.add(c)
    if sort_by is not None and sort_by not in cols:
        raise ValueError("unknown sort column %r" % (sort_by,))
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 0):
        raise ValueError("limit must be a non-negative int")
    rows = [[rec.get(c) for c in cols] for rec in records]
    if sort_by is not None:
        i = cols.index(sort_by)
        present = [r for r in rows if r[i] is not None]
        absent = [r for r in rows if r[i] is None]

        def rank(v):
            if isinstance(v, (int, float)):
                return (0, v)
            return (1, str(v))

        present.sort(key=lambda r: rank(r[i]), reverse=descending)
        rows = present + absent
    if limit is not None:
        rows = rows[:limit]
    if fmt == "csv":
        if not cols:
            return ""

        def cell(v):
            if v is None:
                s = ""
            elif v is True:
                s = "true"
            elif v is False:
                s = "false"
            elif isinstance(v, float):
                s = ("%.2f" % v).rstrip("0").rstrip(".")
            else:
                s = str(v)
            if any(ch in s for ch in ',"\r\n') or s != s.strip(" "):
                s = '"' + s.replace('"', '""') + '"'
            return s

        out = [",".join(cell(c) for c in cols)]
        for r in rows:
            out.append(",".join(cell(v) for v in r))
        return "\n".join(out) + "\n"
    if fmt == "json":
        return json.dumps([dict(zip(cols, r)) for r in rows], indent=2, ensure_ascii=False)
    if not cols:
        return "(no data)"

    def tcell(v):
        if v is None:
            return "-"
        if v is True:
            return "yes"
        if v is False:
            return "no"
        if isinstance(v, float):
            return "%.2f" % v
        return str(v)

    cells = [[tcell(v) for v in r] for r in rows]
    numeric = []
    for i in range(len(cols)):
        vals = [r[i] for r in rows if r[i] is not None]
        numeric.append(bool(vals) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals))
    widths = [max([len(str(c))] + [len(row[i]) for row in cells]) for i, c in enumerate(cols)]

    def line(items):
        parts = [it.rjust(w) if numeric[i] else it.ljust(w)
                 for i, (it, w) in enumerate(zip(items, widths))]
        return "  ".join(parts).rstrip()

    out = [line([str(c) for c in cols]), "  ".join("-" * w for w in widths)]
    out += [line(row) for row in cells]
    return "\n".join(out)


if __name__ == "__main__":
    unittest.main()

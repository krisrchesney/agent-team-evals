import contextlib
import io
import json
import os
import tempfile
import unittest

from logpipe import ConfigError, ParseError, Record, parse_line, parse_lines, run_pipeline
from logpipe.cli import main


def pipe(lines, *filters, transforms=(), fmt="text", **kw):
    return run_pipeline(lines, filters, transforms, fmt, **kw)


class HiddenLogpipe(unittest.TestCase):
    # R1: fields

    def test_r1_record_fields_default(self):
        self.assertEqual(Record(1, "INFO", "x").fields, {})
        self.assertEqual(parse_line("1 INFO plain message").fields, {})

    def test_r1_parse_fields(self):
        rec = parse_line('100 INFO user logged in | user=bob id=7 note="two words" empty=""')
        self.assertEqual((rec.ts, rec.level, rec.msg), (100, "INFO", "user logged in"))
        self.assertEqual(rec.fields, {"user": "bob", "id": "7", "note": "two words", "empty": ""})
        self.assertEqual(list(rec.fields), ["user", "id", "note", "empty"])

    def test_r1_value_may_contain_equals_and_pipes(self):
        rec = parse_line("1 WARN x | expr=a=b path=/a|b")
        self.assertEqual(rec.fields, {"expr": "a=b", "path": "/a|b"})

    def test_r1_splits_at_the_first_separator_only(self):
        with self.assertRaises(ParseError) as ctx:
            parse_line("1 INFO a | b | c=1", 9)
        self.assertEqual(str(ctx.exception), "line 9: bad fields 'b | c=1'")
        rec = parse_line('1 INFO a | note="x | y" c=1')
        self.assertEqual((rec.msg, rec.fields), ("a", {"note": "x | y", "c": "1"}))

    def test_r1_message_is_stripped_and_keeps_inner_spacing(self):
        rec = parse_line("1 INFO   two  spaces   | k=v")
        self.assertEqual(rec.msg, "two  spaces")

    def test_r1_pipe_without_spaces_stays_in_the_message(self):
        rec = parse_line("1 INFO a|b c |d")
        self.assertEqual((rec.msg, rec.fields), ("a|b c |d", {}))

    def test_r1_later_duplicate_key_wins(self):
        self.assertEqual(parse_line("1 INFO m | k=1 k=2").fields["k"], "2")

    def test_r1_bad_fields_raise_parse_error(self):
        for bad in ["oops", "k", "=x", 'k="open', "1k=v", "k=", "a=1 oops"]:
            with self.assertRaises(ParseError, msg=bad) as ctx:
                parse_line(f"5 INFO m | {bad}", 5)
            self.assertEqual(str(ctx.exception), f"line 5: bad fields '{bad}'")

    def test_r1_bad_fields_message_strips_the_fields_part(self):
        with self.assertRaises(ParseError) as ctx:
            parse_line("5 INFO m |   nope  ", 2)
        self.assertEqual(str(ctx.exception), "line 2: bad fields 'nope'")

    def test_r1_line_numbers_count_blank_lines(self):
        with self.assertRaises(ParseError) as ctx:
            list(parse_lines(["1 INFO ok | a=1", "", "2 INFO bad | oops"]))
        self.assertEqual(str(ctx.exception), "line 3: bad fields 'oops'")

    # R2: field, since, until

    LOG = [
        "100 INFO login | user=bob team=a",
        "110 WARN slow | user=amy team=a",
        "120 ERROR crash | user=bob team=b",
        "130 INFO plain",
    ]

    def test_r2_field_filter(self):
        out = pipe(self.LOG, "field:user=bob")
        self.assertEqual([l.split()[0] for l in out], ["100", "120"])

    def test_r2_field_filter_exact_value_and_missing_key(self):
        self.assertEqual(pipe(self.LOG, "field:user=bo"), [])
        self.assertEqual(pipe(self.LOG, "field:nothing=x"), [])

    def test_r2_field_filter_splits_at_first_equals(self):
        out = pipe(["1 INFO a | expr=a=b", "2 INFO b | expr=a"], "field:expr=a=b")
        self.assertEqual([l.split()[0] for l in out], ["1"])

    def test_r2_field_filter_empty_value(self):
        out = pipe(['1 INFO a | k=""', "2 INFO b | k=x", "3 INFO c"], "field:k=")
        self.assertEqual([l.split()[0] for l in out], ["1"])

    def test_r2_field_filter_needs_equals(self):
        with self.assertRaises(ConfigError) as ctx:
            pipe(self.LOG, "field:user")
        self.assertEqual(str(ctx.exception), "bad field filter 'user'")

    def test_r2_since_is_inclusive_until_is_exclusive(self):
        self.assertEqual([l.split()[0] for l in pipe(self.LOG, "since:110")], ["110", "120", "130"])
        self.assertEqual([l.split()[0] for l in pipe(self.LOG, "until:120")], ["100", "110"])
        self.assertEqual([l.split()[0] for l in pipe(self.LOG, "since:110", "until:130")], ["110", "120"])

    def test_r2_bad_timestamp(self):
        for spec, arg in [("since:soon", "soon"), ("until:", ""), ("since:1.5", "1.5")]:
            with self.assertRaises(ConfigError, msg=spec) as ctx:
                pipe(self.LOG, spec)
            self.assertEqual(str(ctx.exception), f"bad timestamp '{arg}'")

    # R3: not

    def test_r3_not_level(self):
        out = pipe(self.LOG, "not:level:warn")
        self.assertEqual([l.split()[0] for l in out], ["100", "130"])

    def test_r3_not_field_keeps_records_without_the_field(self):
        out = pipe(self.LOG, "not:field:user=bob")
        self.assertEqual([l.split()[0] for l in out], ["110", "130"])

    def test_r3_double_negation(self):
        self.assertEqual(pipe(self.LOG, "not:not:level:warn"), pipe(self.LOG, "level:warn"))

    def test_r3_not_combines_with_other_filters(self):
        out = pipe(self.LOG, "not:contains:crash", "since:110")
        self.assertEqual([l.split()[0] for l in out], ["110", "130"])

    def test_r3_not_with_unknown_inner_filter(self):
        with self.assertRaises(ConfigError) as ctx:
            pipe(self.LOG, "not:nope:1")
        self.assertEqual(str(ctx.exception), "unknown filter 'nope'")

    def test_r3_not_passes_errors_through(self):
        with self.assertRaises(ConfigError) as ctx:
            pipe(self.LOG, "not:since:abc")
        self.assertEqual(str(ctx.exception), "bad timestamp 'abc'")

    # R4: dedupe

    REPEATS = ["100 WARN disk full", "102 WARN disk full", "104 WARN disk full", "105 WARN disk full",
               "106 WARN disk full", "110 WARN disk full"]

    def test_r4_window_runs_from_the_last_kept_record(self):
        out = pipe(self.REPEATS, transforms=["dedupe:5"])
        self.assertEqual([l.split()[0] for l in out], ["100", "105", "110"])

    def test_r4_boundary_is_exclusive(self):
        out = pipe(["0 INFO a", "9 INFO a", "10 INFO a"], transforms=["dedupe:10"])
        self.assertEqual([l.split()[0] for l in out], ["0", "10"])

    def test_r4_level_and_message_both_matter(self):
        lines = ["1 INFO a", "2 WARN a", "3 INFO b", "4 INFO a"]
        out = pipe(lines, transforms=["dedupe:100"])
        self.assertEqual([l.split()[0] for l in out], ["1", "2", "3"])

    def test_r4_fields_are_ignored(self):
        lines = ["1 INFO a | k=1", "2 INFO a | k=2"]
        self.assertEqual(len(pipe(lines, transforms=["dedupe:10"])), 1)

    def test_r4_sees_the_message_as_earlier_transforms_left_it(self):
        lines = ["1 INFO Retry", "2 INFO RETRY"]
        self.assertEqual(len(pipe(lines, transforms=["upper", "dedupe:10"])), 1)
        self.assertEqual(len(pipe(lines, transforms=["dedupe:10", "upper"])), 2)

    def test_r4_dropped_records_do_not_extend_the_window(self):
        lines = ["0 INFO a", "4 INFO a", "8 INFO a", "12 INFO a"]
        out = pipe(lines, transforms=["dedupe:10"])
        self.assertEqual([l.split()[0] for l in out], ["0", "12"])

    def test_r4_only_filtered_in_records_count(self):
        lines = ["1 INFO a | keep=no", "2 INFO a | keep=yes"]
        out = pipe(lines, "field:keep=yes", transforms=["dedupe:10"])
        self.assertEqual([l.split()[0] for l in out], ["2"])

    def test_r4_bad_window(self):
        for arg in ["0", "-3", "x", "1.5", ""]:
            with self.assertRaises(ConfigError, msg=repr(arg)) as ctx:
                pipe(self.REPEATS, transforms=[f"dedupe:{arg}"])
            self.assertEqual(str(ctx.exception), f"bad dedupe window '{arg}'")

    # R5: rename

    def test_r5_rename_keeps_position(self):
        (line,) = pipe(["1 INFO m | a=1 b=2 c=3"], transforms=["rename:b=beta"])
        self.assertEqual(line, "1 INFO m | a=1 beta=2 c=3")

    def test_r5_rename_replaces_an_existing_field(self):
        (line,) = pipe(["1 INFO m | a=1 b=2 c=3"], transforms=["rename:c=a"])
        self.assertEqual(line, "1 INFO m | b=2 a=3")

    def test_r5_rename_replaces_a_later_field_too(self):
        (line,) = pipe(["1 INFO m | a=1 b=2 c=3"], transforms=["rename:a=c"])
        self.assertEqual(line, "1 INFO m | c=1 b=2")

    def test_r5_rename_missing_field_and_no_fields(self):
        out = pipe(["1 INFO m | a=1", "2 INFO n"], transforms=["rename:zzz=y"])
        self.assertEqual(out, ["1 INFO m | a=1", "2 INFO n"])

    def test_r5_rename_to_itself(self):
        (line,) = pipe(["1 INFO m | a=1 b=2"], transforms=["rename:a=a"])
        self.assertEqual(line, "1 INFO m | a=1 b=2")

    def test_r5_renames_chain(self):
        (line,) = pipe(["1 INFO m | a=1"], transforms=["rename:a=b", "rename:b=c"])
        self.assertEqual(line, "1 INFO m | c=1")

    def test_r5_bad_rename(self):
        for arg in ["a", "=b", "a=", "", "="]:
            with self.assertRaises(ConfigError, msg=repr(arg)) as ctx:
                pipe(["1 INFO m | a=1"], transforms=[f"rename:{arg}"])
            self.assertEqual(str(ctx.exception), f"bad rename '{arg}'")

    # R6: formats

    def test_r6_text_with_fields(self):
        (line,) = pipe(['7 WARN hello world | user=bob note="two words" empty=""'])
        self.assertEqual(line, '7 WARN hello world | user=bob note="two words" empty=""')

    def test_r6_text_without_fields_is_unchanged(self):
        self.assertEqual(pipe(["7 WARN hello  world"]), ["7 WARN hello  world"])

    def test_r6_json_has_fields(self):
        (line,) = pipe(['7 WARN hi | user=bob note="a b"'], fmt="json")
        self.assertEqual(json.loads(line), {"ts": 7, "level": "WARN", "msg": "hi",
                                            "fields": {"user": "bob", "note": "a b"}})

    def test_r6_json_without_fields_has_an_empty_object(self):
        (line,) = pipe(["7 WARN hi"], fmt="json")
        self.assertEqual(json.loads(line), {"ts": 7, "level": "WARN", "msg": "hi", "fields": {}})

    # R7: pipeline order, drops and stats

    def test_r7_stats_counts(self):
        lines = [
            "1 INFO a | k=1",
            "2 DEBUG noise",
            "3 INFO a | k=1",
            "",
            "4 WARN b",
            "5 INFO c",
        ]
        stats = {"junk": 1}
        out = run_pipeline(lines, ["level:info"], ["dedupe:10"], "text", stats=stats)
        self.assertEqual(out, ["1 INFO a | k=1", "4 WARN b", "5 INFO c"])
        self.assertEqual(stats, {"read": 5, "skipped": 0, "filtered": 1, "deduped": 1, "emitted": 3})

    def test_r7_stats_identity(self):
        stats = {}
        run_pipeline(self.REPEATS, ["since:101"], ["dedupe:5"], "text", stats=stats)
        self.assertEqual(stats["read"], stats["filtered"] + stats["deduped"] + stats["emitted"])
        self.assertEqual((stats["read"], stats["filtered"], stats["deduped"], stats["emitted"]),
                         (6, 1, 3, 2))

    def test_r7_stats_default_is_off(self):
        self.assertEqual(run_pipeline(["1 INFO a"]), ["1 INFO a"])

    def test_r7_filters_come_before_transforms(self):
        out = pipe(["1 INFO secret stuff"], "contains:secret", transforms=["redact:secret"])
        self.assertEqual(out, ["1 INFO *** stuff"])
        out = pipe(["1 INFO secret stuff"], "contains:***", transforms=["redact:secret"])
        self.assertEqual(out, [])

    def test_r7_signature(self):
        out = run_pipeline(["1 INFO a"], (), (), "json", False, None)
        self.assertEqual(json.loads(out[0])["msg"], "a")

    # R8: lenient

    BAD = ["1 INFO ok", "garbage", "3 LOUD x", "4 INFO ok | oops", "", "5 INFO fine | a=1"]

    def test_r8_strict_raises_at_the_first_bad_line(self):
        with self.assertRaises(ParseError) as ctx:
            pipe(self.BAD)
        self.assertEqual(str(ctx.exception), "line 2: expected '<ts> <LEVEL> <message>'")

    def test_r8_lenient_skips_and_counts(self):
        stats = {}
        out = pipe(self.BAD, lenient=True, stats=stats)
        self.assertEqual(out, ["1 INFO ok", "5 INFO fine | a=1"])
        self.assertEqual(stats, {"read": 2, "skipped": 3, "filtered": 0, "deduped": 0, "emitted": 2})

    def test_r8_lenient_keeps_filters_working(self):
        stats = {}
        out = pipe(self.BAD, "field:a=1", lenient=True, stats=stats)
        self.assertEqual(out, ["5 INFO fine | a=1"])
        self.assertEqual((stats["read"], stats["skipped"], stats["filtered"]), (2, 3, 1))

    def test_r8_lenient_with_nothing_wrong(self):
        stats = {}
        pipe(["1 INFO a"], lenient=True, stats=stats)
        self.assertEqual(stats["skipped"], 0)

    # R9: state belongs to one run

    def test_r9_same_run_twice_gives_same_output(self):
        first = pipe(self.REPEATS, transforms=["dedupe:5"])
        second = pipe(self.REPEATS, transforms=["dedupe:5"])
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)

    def test_r9_second_run_does_not_see_the_first_runs_records(self):
        pipe(["100 INFO a"], transforms=["dedupe:50"])
        self.assertEqual(pipe(["101 INFO a"], transforms=["dedupe:50"]), ["101 INFO a"])

    def test_r9_two_dedupes_have_separate_memory(self):
        lines = ["0 INFO a", "10 INFO a", "70 INFO a"]
        out = pipe(lines, transforms=["dedupe:5", "dedupe:60"])
        self.assertEqual([l.split()[0] for l in out], ["0", "70"])

    def test_r9_same_spec_twice_in_one_run_is_two_independent_steps(self):
        lines = ["0 INFO a", "3 INFO a", "6 INFO a"]
        out = pipe(lines, transforms=["dedupe:5", "dedupe:5"])
        # first step keeps 0 and 6; the second step sees only those and keeps both
        self.assertEqual([l.split()[0] for l in out], ["0", "6"])

    # R10: CLI

    def cli(self, text, *extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "app.log")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([path, *extra])
        return code, out.getvalue(), err.getvalue()

    TEXT = "1 INFO a | k=1\nbad line\n2 INFO a | k=1\n3 WARN b\n"

    def test_r10_cli_new_filters_and_transforms(self):
        code, out, err = self.cli(self.TEXT, "--lenient", "--filter", "not:level:warn",
                                  "--transform", "dedupe:10", "--transform", "rename:k=key")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines(), ["1 INFO a | key=1"])

    def test_r10_cli_stats_line(self):
        code, out, err = self.cli(self.TEXT, "--lenient", "--stats", "--transform", "dedupe:10")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["1 INFO a | k=1", "3 WARN b"])
        self.assertEqual(err.splitlines(), ["read=3 skipped=1 filtered=0 deduped=1 emitted=2"])

    def test_r10_cli_no_stats_by_default(self):
        _, _, err = self.cli("1 INFO a\n")
        self.assertEqual(err, "")

    def test_r10_cli_strict_error_prints_nothing_to_stdout(self):
        code, out, err = self.cli(self.TEXT, "--stats")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "logpipe: error: line 2: expected '<ts> <LEVEL> <message>'")

    def test_r10_cli_config_error(self):
        code, out, err = self.cli("1 INFO a\n", "--filter", "since:soon")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "logpipe: error: bad timestamp 'soon'")

    def test_r10_cli_json(self):
        code, out, _ = self.cli("1 INFO a | k=v\n", "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["fields"], {"k": "v"})

    # R11: old behaviour

    OLD = ["1 INFO Hello World", "2 warn disk Almost full", "3 ERROR Crash"]

    def test_r11_old_filters_and_transforms(self):
        self.assertEqual(pipe(self.OLD, "level:warn", transforms=["upper"]),
                         ["2 WARN DISK ALMOST FULL", "3 ERROR CRASH"])
        self.assertEqual(pipe(self.OLD, "contains:Crash"), ["3 ERROR Crash"])
        self.assertEqual(pipe(self.OLD, transforms=["truncate:4", "redact:Hell"])[0], "1 INFO ***")
        self.assertEqual(pipe(self.OLD, transforms=["redact:disk"])[1], "2 WARN *** Almost full")

    def test_r11_old_error_messages(self):
        cases = [
            (["x INFO a"], "line 1: bad timestamp 'x'"),
            (["1 LOUD a"], "line 1: bad level 'LOUD'"),
            (["1 INFO"], "line 1: expected '<ts> <LEVEL> <message>'"),
        ]
        for lines, message in cases:
            with self.assertRaises(ParseError) as ctx:
                pipe(lines)
            self.assertEqual(str(ctx.exception), message)
        with self.assertRaises(ConfigError) as ctx:
            pipe(self.OLD, "level:loud")
        self.assertEqual(str(ctx.exception), "bad level 'loud'")
        with self.assertRaises(ConfigError) as ctx:
            pipe(self.OLD, transforms=["shout"])
        self.assertEqual(str(ctx.exception), "unknown transform 'shout'")
        with self.assertRaises(ConfigError) as ctx:
            pipe(self.OLD, fmt="xml")
        self.assertEqual(str(ctx.exception), "unknown format 'xml'")

    def test_r11_old_transforms_leave_fields_alone(self):
        (line,) = pipe(["1 INFO secret hello | tag=secret"],
                       transforms=["upper", "truncate:8", "redact:SECRET"])
        self.assertEqual(line, "1 INFO *** H | tag=secret")

    def test_r11_blank_lines_are_ignored(self):
        self.assertEqual(pipe(["", "1 INFO a", "   ", "2 INFO b"]), ["1 INFO a", "2 INFO b"])


if __name__ == "__main__":
    unittest.main()

"""Hidden tests for t25-pipeline-plugin. Every rule is shown by the starting code; see AUDIT.md."""
import copy
import io
import json
import os
import tempfile
import unittest

from datapipe import ConfigError, StageError, build_pipeline, build_stage
from datapipe.cli import main
from datapipe.registry import PLUGINS


def sales():
    return [
        {"region": "east", "kind": "a", "amount": 10},
        {"region": "west", "kind": "a", "amount": 4},
        {"region": "east", "kind": "b", "amount": 5},
        {"region": "east", "kind": "a", "amount": 2.5},
        {"region": "west", "kind": "b", "amount": 1},
    ]


def rollup(**options):
    return dict({"type": "rollup", "by": ["region"]}, **options)


class TestResults(unittest.TestCase):
    def test_registered_and_named_after_its_type(self):
        self.assertIn("rollup", PLUGINS)
        self.assertEqual(build_stage(rollup()).name, "rollup")
        self.assertEqual(build_stage(rollup(name="totals")).name, "totals")

    def test_count_is_the_default_and_groups_keep_first_seen_order(self):
        result = build_pipeline([rollup()]).run(sales())
        self.assertEqual(result.records, [{"region": "east", "count": 3}, {"region": "west", "count": 2}])
        result = build_pipeline([rollup()]).run(list(reversed(sales())))
        self.assertEqual([r["region"] for r in result.records], ["west", "east"])

    def test_several_by_fields(self):
        result = build_pipeline([rollup(by=["region", "kind"], field="amount", aggregates=["sum"])]).run(sales())
        self.assertEqual(result.records, [
            {"region": "east", "kind": "a", "sum_amount": 12.5},
            {"region": "west", "kind": "a", "sum_amount": 4},
            {"region": "east", "kind": "b", "sum_amount": 5},
            {"region": "west", "kind": "b", "sum_amount": 1},
        ])

    def test_every_aggregate(self):
        aggs = ["sum", "min", "max", "avg", "count"]
        east, west = build_pipeline([rollup(field="amount", aggregates=aggs)]).run(sales()).records
        self.assertEqual(list(east), ["region", "sum_amount", "min_amount", "max_amount", "avg_amount", "count"])
        self.assertEqual((east["sum_amount"], east["min_amount"], east["max_amount"], east["count"]),
                         (17.5, 2.5, 10, 3))
        self.assertAlmostEqual(east["avg_amount"], 17.5 / 3)
        self.assertEqual((west["sum_amount"], west["min_amount"], west["max_amount"], west["avg_amount"]),
                         (5, 1, 4, 2.5))

    def test_aggregates_come_in_the_order_listed(self):
        rec = build_pipeline([rollup(field="amount", aggregates=["max", "count", "sum"])]).run(sales()).records[0]
        self.assertEqual(list(rec), ["region", "max_amount", "count", "sum_amount"])

    def test_sums_of_whole_numbers_stay_whole(self):
        result = build_pipeline([rollup(field="amount", aggregates=["sum", "min"])]).run(
            [{"region": "x", "amount": 2}, {"region": "x", "amount": 3}])
        self.assertIsInstance(result.records[0]["sum_amount"], int)
        self.assertIsInstance(result.records[0]["min_amount"], int)

    def test_zero_and_empty_string_are_real_group_values(self):
        pipe = build_pipeline([{"type": "rollup", "by": ["code"]}])
        result = pipe.run([{"code": 0}, {"code": ""}, {"code": 0}])
        self.assertEqual(result.dead_letters, [])
        self.assertEqual(result.records, [{"code": 0, "count": 2}, {"code": "", "count": 1}])

    def test_empty_input(self):
        result = build_pipeline([rollup(field="amount", aggregates=["sum"])]).run([])
        self.assertEqual((result.records, result.dead_letters), ([], []))

    def test_count_only_does_not_read_the_field(self):
        result = build_pipeline([rollup(field="amount")]).run([{"region": "e"}, {"region": "e", "amount": "x"}])
        self.assertEqual(result.records, [{"region": "e", "count": 2}])
        self.assertEqual(result.dead_letters, [])


class TestLifecycle(unittest.TestCase):
    def test_nothing_is_emitted_before_the_input_ends(self):
        pipe = build_pipeline([rollup(), {"type": "map", "set": {"seen": True}}])
        result = pipe.run(sales())
        self.assertEqual(result.stats["rollup"], {"in": 5, "out": 2, "rejected": 0})
        self.assertEqual(result.stats["map"], {"in": 2, "out": 2, "rejected": 0})
        self.assertTrue(all(r["seen"] for r in result.records))

    def test_flushed_results_go_through_the_stages_after_it(self):
        pipe = build_pipeline([rollup(), {"type": "filter", "field": "count", "op": "gt", "value": 2}])
        self.assertEqual(pipe.run(sales()).records, [{"region": "east", "count": 3}])

    def test_flushed_results_that_a_later_stage_rejects_become_dead_letters(self):
        pipe = build_pipeline([rollup(), {"type": "lookup", "field": "region", "into": "name",
                                          "table": {"east": "East"}}])
        result = pipe.run(sales())
        self.assertEqual(result.records, [{"region": "east", "count": 3, "name": "East"}])
        self.assertEqual([(d["stage"], d["index"]) for d in result.dead_letters], [("lookup", 1)])
        self.assertEqual(result.dead_letters[0]["record"], {"region": "west", "count": 2})

    def test_a_stage_before_it_can_flush_into_it(self):
        pipe = build_pipeline([{"type": "batch", "size": 2}, {"type": "rollup", "by": ["size"]}])
        result = pipe.run([{"n": n} for n in range(5)])
        self.assertEqual(result.records, [{"size": 2, "count": 2}, {"size": 1, "count": 1}])

    def test_each_run_starts_empty(self):
        pipe = build_pipeline([rollup(field="amount", aggregates=["sum"])])
        first = pipe.run(sales()).records
        second = pipe.run([{"region": "north", "amount": 7}]).records
        self.assertEqual(second, [{"region": "north", "sum_amount": 7}])
        self.assertEqual(pipe.run(sales()).records, first)
        self.assertEqual(pipe.run([]).records, [])

    def test_flushing_empties_the_stage(self):
        stage = build_stage(rollup())
        dead = []
        stage.reset()
        stage.open(None)
        for rec in sales():
            self.assertEqual(stage.handle(rec, dead), [])
        self.assertEqual(len(stage.run_flush()), 2)
        self.assertEqual(stage.run_flush(), [])

    def test_inputs_are_not_changed_and_outputs_are_new(self):
        records = sales()
        before = copy.deepcopy(records)
        result = build_pipeline([rollup(field="amount", aggregates=["sum"])]).run(records)
        self.assertEqual(records, before)
        for out in result.records:
            self.assertTrue(all(out is not r for r in records))


class TestRejects(unittest.TestCase):
    def run_bad(self, records, **options):
        return build_pipeline([rollup(field="amount", aggregates=["sum", "count"], **options)]).run(records)

    def test_bad_records_are_rejected_with_the_stage_name_and_position(self):
        bad = [
            {"amount": 1},                                # no region
            {"region": None, "amount": 1},                # region is None
            {"region": ["e"], "amount": 1},               # unusable as a key
            {"region": "east"},                           # no amount
            {"region": "east", "amount": None},           # amount is None
            {"region": "east", "amount": "12"},           # not a number
            {"region": "east", "amount": True},           # a bool is not a number
        ]
        good = {"region": "east", "amount": 3}
        result = self.run_bad([good] + bad + [good])
        self.assertEqual(result.records, [{"region": "east", "sum_amount": 6, "count": 2}])
        self.assertEqual([d["index"] for d in result.dead_letters], list(range(1, 8)))
        for letter, record in zip(result.dead_letters, bad):
            self.assertEqual(letter["stage"], "rollup")
            self.assertIs(letter["record"], record)
            self.assertIsInstance(letter["reason"], str)
        self.assertIn("region", result.dead_letters[0]["reason"])
        self.assertIn("amount", result.dead_letters[3]["reason"])
        self.assertEqual(result.stats["rollup"], {"in": 9, "out": 1, "rejected": 7})

    def test_a_rejected_record_does_not_create_a_group(self):
        result = self.run_bad([{"region": "east", "amount": 1}, {"region": "ghost", "amount": "x"},
                               {"region": "west", "amount": 2}])
        self.assertEqual([r["region"] for r in result.records], ["east", "west"])
        self.assertEqual(len(result.dead_letters), 1)

    def test_on_reject_fail_stops_the_run(self):
        with self.assertRaises(StageError) as ctx:
            self.run_bad([{"region": "e", "amount": 1}, {"region": "e", "amount": "x"}], on_reject="fail")
        self.assertEqual((ctx.exception.stage, ctx.exception.index), ("rollup", 1))


class TestConfig(unittest.TestCase):
    def test_bad_config_is_a_config_error_when_the_pipeline_is_built(self):
        bad = {
            "no by": {"type": "rollup"},
            "empty by": rollup(by=[]),
            "by is a string": rollup(by="region"),
            "by has a non-string": rollup(by=["region", 3]),
            "by has an empty name": rollup(by=[""]),
            "empty aggregates": rollup(aggregates=[]),
            "aggregates is a string": rollup(aggregates="count"),
            "unknown aggregate": rollup(field="amount", aggregates=["median"]),
            "repeated aggregate": rollup(field="amount", aggregates=["sum", "sum"]),
            "sum without field": rollup(aggregates=["sum"]),
            "count and max without field": rollup(aggregates=["count", "max"]),
            "field is not a string": rollup(field=3, aggregates=["sum"]),
            "field is empty": rollup(field="", aggregates=["sum"]),
            "unknown option": rollup(colour="red"),
            "bad on_reject": rollup(on_reject="shrug"),
        }
        for label, spec in bad.items():
            with self.subTest(label):
                with self.assertRaises(ConfigError) as ctx:
                    build_pipeline([spec])
                self.assertEqual(ctx.exception.stage, "rollup")
                self.assertTrue(str(ctx.exception).startswith("stage 'rollup': "))

    def test_the_error_names_the_stage_by_its_name(self):
        with self.assertRaises(ConfigError) as ctx:
            build_pipeline([rollup(name="totals", by=[])])
        self.assertEqual(ctx.exception.stage, "totals")

    def test_valid_options_are_accepted(self):
        for aggregates in (["count"], ["sum"], ["avg", "min", "max", "sum", "count"]):
            build_pipeline([rollup(field="amount", aggregates=aggregates)])
        build_pipeline([rollup(aggregates=["count"], on_reject="fail"), rollup(name="second")])

    def test_stage_names_must_be_unique(self):
        with self.assertRaises(ConfigError):
            build_pipeline([rollup(), rollup()])


class TestEverywhere(unittest.TestCase):
    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, data = os.path.join(tmp, "p.json"), os.path.join(tmp, "in.jsonl")
            with open(cfg, "w", encoding="utf-8") as fh:
                json.dump([rollup(field="amount", aggregates=["sum"])], fh)
            with open(data, "w", encoding="utf-8") as fh:
                fh.write("\n".join(json.dumps(r) for r in sales() + [{"amount": 1}]) + "\n")
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(main([cfg, data], stdout=out, stderr=err), 0)
        lines = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(lines, [{"region": "east", "sum_amount": 17.5}, {"region": "west", "sum_amount": 5}])
        self.assertEqual(err.getvalue(), "datapipe: 1 record(s) rejected\n")

    def test_other_stages_unchanged(self):
        result = build_pipeline([{"type": "dedupe", "key": ["region", "kind"]}]).run(sales())
        self.assertEqual(len(result.records), 4)


if __name__ == "__main__":
    unittest.main()

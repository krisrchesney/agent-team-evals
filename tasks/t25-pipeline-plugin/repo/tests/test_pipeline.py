import unittest

from datapipe import ConfigError, StageError, build_pipeline


class PipelineTest(unittest.TestCase):
    def test_filter_and_map(self):
        pipe = build_pipeline([
            {"type": "filter", "field": "amount", "op": "gt", "value": 0},
            {"type": "map", "rename": {"amount": "total"}, "set": {"source": "test"}},
        ])
        result = pipe.run([{"id": 1, "amount": 5}, {"id": 2, "amount": -1}])
        self.assertEqual(result.records, [{"id": 1, "total": 5, "source": "test"}])
        self.assertEqual(result.stats["filter"], {"in": 2, "out": 1, "rejected": 0})

    def test_bad_records_become_dead_letters(self):
        pipe = build_pipeline([{"type": "filter", "field": "amount", "op": "gt", "value": 0}])
        result = pipe.run([{"id": 1}, {"id": 2, "amount": "x"}, {"id": 3, "amount": 4}])
        self.assertEqual([r["id"] for r in result.records], [3])
        self.assertEqual([(d["stage"], d["index"]) for d in result.dead_letters], [("filter", 0), ("filter", 1)])
        self.assertEqual(result.stats["filter"]["rejected"], 2)

    def test_on_reject_fail_stops_the_run(self):
        pipe = build_pipeline([{"type": "filter", "field": "amount", "op": "gt", "value": 0,
                                "on_reject": "fail"}])
        with self.assertRaises(StageError) as ctx:
            pipe.run([{"amount": 1}, {"amount": "x"}])
        self.assertEqual((ctx.exception.stage, ctx.exception.index), ("filter", 1))

    def test_batch_flushes_the_partial_batch(self):
        pipe = build_pipeline([{"type": "batch", "size": 2}])
        result = pipe.run([{"n": 1}, {"n": 2}, {"n": 3}])
        self.assertEqual([r["size"] for r in result.records], [2, 1])

    def test_dedupe_starts_fresh_each_run(self):
        pipe = build_pipeline([{"type": "dedupe", "key": ["id"]}])
        self.assertEqual(len(pipe.run([{"id": 1}, {"id": 1}]).records), 1)
        self.assertEqual(len(pipe.run([{"id": 1}]).records), 1)

    def test_config_errors(self):
        for spec in ({"type": "nope"}, {"type": "batch"}, {"type": "batch", "size": 0},
                     {"type": "filter", "field": "a", "op": "zz", "value": 1},
                     {"type": "dedupe", "key": ["a"], "colour": "red"}):
            with self.assertRaises(ConfigError):
                build_pipeline([spec])

    def test_lookup_and_cast(self):
        pipe = build_pipeline([
            {"type": "map", "cast": {"qty": "int"}},
            {"type": "lookup", "field": "sku", "into": "name", "table": {"a": "Apple"}, "default": "?"},
        ])
        result = pipe.run([{"sku": "a", "qty": "3"}, {"sku": "z", "qty": "x"}])
        self.assertEqual(result.records, [{"sku": "a", "qty": 3, "name": "Apple"}])
        self.assertEqual(len(result.dead_letters), 1)


if __name__ == "__main__":
    unittest.main()

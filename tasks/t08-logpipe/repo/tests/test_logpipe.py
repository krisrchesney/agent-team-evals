import unittest

from logpipe import ConfigError, ParseError, parse_line, run_pipeline

LOG = [
    "100 INFO service started",
    "105 WARN disk almost full",
    "",
    "110 ERROR crash in worker",
]


class TestLogpipe(unittest.TestCase):
    def test_parse_line(self):
        rec = parse_line("100 info  hello   world ")
        self.assertEqual((rec.ts, rec.level, rec.msg), (100, "INFO", "hello   world"))

    def test_bad_level(self):
        with self.assertRaises(ParseError):
            parse_line("100 LOUD hi", 4)

    def test_filter_and_transform(self):
        out = run_pipeline(LOG, filters=["level:warn"], transforms=["upper"])
        self.assertEqual(out, ["105 WARN DISK ALMOST FULL", "110 ERROR CRASH IN WORKER"])

    def test_unknown_filter(self):
        with self.assertRaises(ConfigError):
            run_pipeline(LOG, filters=["nope:1"])


if __name__ == "__main__":
    unittest.main()

import unittest

from migrator.clock import FixedClock, iso
from migrator.sql import split_statements


class SqlSplitTest(unittest.TestCase):
    def test_splits_statements(self):
        script = "CREATE TABLE a (id INTEGER);\nINSERT INTO a VALUES (1);\n"
        self.assertEqual(split_statements(script), ["CREATE TABLE a (id INTEGER);", "INSERT INTO a VALUES (1);"])

    def test_keeps_semicolons_inside_triggers(self):
        script = "CREATE TRIGGER t AFTER INSERT ON a BEGIN\n  UPDATE a SET id = 2;\nEND;\nSELECT 1;"
        self.assertEqual(len(split_statements(script)), 2)

    def test_comment_only_script_is_empty(self):
        self.assertEqual(split_statements("-- nothing to do\n\n"), [])


class ClockTest(unittest.TestCase):
    def test_fixed_clock(self):
        c = FixedClock()
        c.advance(minutes=5)
        self.assertEqual(iso(c.now()), "2026-03-02T08:05:00Z")

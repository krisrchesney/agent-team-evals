import unittest

from tracelens import make, run
from tracelens.analysis.funnel import funnel
from tracelens.analysis.sessions import sessionize
from tracelens.ingest.dedupe import dedupe
from tracelens.ingest.logparse import parse_line
from tracelens.reports.pages import top_pages


class BasicTest(unittest.TestCase):
    def test_dedupe_keeps_the_earliest_copy(self):
        a = make("e1", "u1", 200)
        b = make("e1", "u1", 100)
        self.assertEqual(dedupe([a, b]), [b])

    def test_sessions_split_on_a_long_gap(self):
        events = [make("e1", "u1", 0), make("e2", "u1", 1000), make("e3", "u1", 5000)]
        sessions = sessionize(events, gap_ms=1000)
        self.assertEqual([(s.id, s.events) for s in sessions], [("s_000001", 2), ("s_000002", 1)])

    def test_top_pages_counts_views(self):
        events = [make("1", "u", 1, page="/a"), make("2", "u", 2, page="/b"), make("3", "v", 3, page="/b"),
                  make("4", "v", 4, kind="click", page="/a")]
        self.assertEqual(top_pages(events, 5), [("/b", 2), ("/a", 1)])

    def test_funnel(self):
        events = [make("1", "u", 1, page="/a"), make("2", "u", 2, page="/b"), make("3", "v", 3, page="/a")]
        self.assertEqual(funnel(events, ["/a", "/b"]), [2, 1])

    def test_pipeline(self):
        events = [make("1", "u", 1, page="/a"), make("1", "u", 5, page="/a"), make("2", "u", 9, page="/b")]
        result = run(events, funnel_steps=["/a", "/b"])
        self.assertEqual((result["events"], result["duplicates"], result["sessions"]), (2, 1, 1))
        self.assertEqual(result["funnel"], [1, 1])

    def test_parse_line(self):
        e = parse_line("2026-03-01T10:15:30.250Z shard=2 seq=7 id=a user=u1 kind=view page=/x ref=http://h")
        self.assertEqual((e.id, e.shard, e.seq, e.page, e.props), ("a", 2, 7, "/x", {"ref": "http://h"}))


if __name__ == "__main__":
    unittest.main()

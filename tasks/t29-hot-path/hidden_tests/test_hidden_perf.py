"""Hidden tests for t29-hot-path. Behaviour is pinned on small inputs; speed is checked on 40,000 events.

Each speed test runs in a child process with a hard timeout, so a quadratic implementation fails
quickly instead of hanging. See AUDIT.md for the budgets.
"""
import json
import os
import random
import subprocess
import sys
import unittest

from tracelens import make, run
from tracelens.analysis.funnel import funnel
from tracelens.analysis.sessions import bounce_rate, sessionize
from tracelens.ingest.dedupe import dedupe, duplicate_count
from tracelens.reports.pages import top_pages


def ids(events):
    return [e.id for e in events]


class TestDedupe(unittest.TestCase):
    def test_reg_earliest_copy_wins_and_result_is_sorted(self):
        a = make("x", "u", 200, seq=1)
        b = make("x", "u", 100, seq=2)
        c = make("y", "u", 150)
        self.assertEqual(ids(dedupe([a, b, c])), ["x", "y"])
        self.assertEqual(dedupe([a, b, c])[0].ts, 100)

    def test_reg_ties_go_to_the_lower_shard_then_seq(self):
        a = make("x", "u", 100, shard=2, seq=1)
        b = make("x", "u", 100, shard=1, seq=9)
        c = make("x", "u", 100, shard=1, seq=3)
        (kept,) = dedupe([a, b, c])
        self.assertEqual((kept.shard, kept.seq), (1, 3))

    def test_reg_input_is_not_changed_and_empty_is_fine(self):
        events = [make("b", "u", 2), make("a", "u", 1), make("a", "u", 3)]
        before = list(events)
        out = dedupe(events)
        self.assertEqual(events, before)
        self.assertIsNot(out, events)
        self.assertEqual(dedupe([]), [])
        self.assertEqual(duplicate_count(events), 1)

    def test_reg_same_id_for_different_users_is_still_one_event(self):
        self.assertEqual(len(dedupe([make("x", "u1", 1), make("x", "u2", 2)])), 1)


class TestSessions(unittest.TestCase):
    def test_reg_exactly_the_gap_continues_the_session(self):
        events = [make("1", "u", 0), make("2", "u", 1000), make("3", "u", 2001)]
        sessions = sessionize(events, gap_ms=1000)
        self.assertEqual([(s.start, s.end, s.events) for s in sessions], [(0, 1000, 2), (2001, 2001, 1)])

    def test_reg_the_gap_is_measured_from_the_last_event_of_the_session(self):
        events = [make(str(i), "u", i * 900) for i in range(5)]
        (only,) = sessionize(events, gap_ms=1000)
        self.assertEqual((only.start, only.end, only.events), (0, 3600, 5))

    def test_reg_users_are_independent_and_ids_follow_start_order(self):
        events = [make("1", "a", 0), make("2", "b", 10), make("3", "a", 5000), make("4", "b", 20), make("5", "a", 5001)]
        sessions = sessionize(events, gap_ms=1000)
        self.assertEqual([(s.id, s.user, s.events) for s in sessions],
                         [("s_000001", "a", 1), ("s_000002", "b", 2), ("s_000003", "a", 2)])

    def test_reg_input_order_does_not_matter(self):
        events = [make(str(i), f"u{i % 3}", i * 400, shard=i % 2, seq=i) for i in range(40)]
        shuffled = list(events)
        random.Random(3).shuffle(shuffled)
        a = [(s.id, s.user, s.start, s.end, s.events, s.pages) for s in sessionize(events, 1000)]
        b = [(s.id, s.user, s.start, s.end, s.events, s.pages) for s in sessionize(shuffled, 1000)]
        self.assertEqual(a, b)

    def test_reg_pings_do_not_count_or_extend_sessions(self):
        events = [make("1", "u", 0), make("2", "u", 900, kind="ping"), make("3", "u", 1800)]
        sessions = sessionize(events, gap_ms=1000)
        self.assertEqual([(s.start, s.end, s.events) for s in sessions], [(0, 0, 1), (1800, 1800, 1)])

    def test_reg_pages_are_listed_once_in_first_visit_order(self):
        events = [make("1", "u", 1, page="/b"), make("2", "u", 2, page="/a"), make("3", "u", 3, page="/b")]
        (s,) = sessionize(events)
        self.assertEqual(s.pages, ["/b", "/a"])

    def test_reg_bounce_rate(self):
        events = [make("1", "a", 0), make("2", "b", 0), make("3", "b", 5)]
        self.assertEqual(bounce_rate(sessionize(events)), 0.5)


class TestTopPages(unittest.TestCase):
    def setUp(self):
        self.events = [
            make("1", "u1", 1, page="/b"), make("2", "u1", 2, page="/b"), make("3", "u2", 3, page="/a"),
            make("4", "u2", 4, page="/a"), make("5", "u3", 5, page="/c"), make("6", "u3", 6, kind="click", page="/c"),
            make("7", "u3", 7, page="/b"),
        ]

    def test_reg_counts_and_tie_order(self):
        self.assertEqual(top_pages(self.events, 10), [("/b", 3), ("/a", 2), ("/c", 1)])

    def test_reg_n_limits_and_none_means_all(self):
        self.assertEqual(top_pages(self.events, 1), [("/b", 3)])
        self.assertEqual(len(top_pages(self.events, None)), 3)

    def test_reg_unique_users_count_each_user_once(self):
        self.assertEqual(top_pages(self.events, None, unique_users=True), [("/b", 2), ("/a", 1), ("/c", 1)])

    def test_reg_ties_are_broken_by_page_name(self):
        events = [make("1", "u", 1, page="/z"), make("2", "u", 2, page="/m")]
        self.assertEqual(top_pages(events), [("/m", 1), ("/z", 1)])


class TestFunnel(unittest.TestCase):
    def test_reg_steps_must_be_viewed_in_order(self):
        events = [make("1", "u", 1, page="/b"), make("2", "u", 2, page="/a"), make("3", "u", 3, page="/b"),
                  make("4", "v", 1, page="/b")]
        self.assertEqual(funnel(events, ["/a", "/b"]), [1, 1])

    def test_reg_repeats_do_not_count_twice_and_clicks_are_ignored(self):
        events = [make("1", "u", 1, page="/a"), make("2", "u", 2, page="/a"), make("3", "u", 3, kind="click", page="/b")]
        self.assertEqual(funnel(events, ["/a", "/b"]), [1, 0])

    def test_reg_users_are_independent_and_empty_cases(self):
        events = [make("1", "u", 1, page="/a"), make("2", "v", 2, page="/a"), make("3", "v", 3, page="/b")]
        self.assertEqual(funnel(events, ["/a", "/b"]), [2, 1])
        self.assertEqual(funnel([], ["/a"]), [0])
        self.assertEqual(funnel(events, []), [])

    def test_reg_order_uses_the_sort_key_not_the_list_order(self):
        events = [make("2", "u", 5, page="/b"), make("1", "u", 1, page="/a")]
        self.assertEqual(funnel(events, ["/a", "/b"]), [1, 1])


class TestPipeline(unittest.TestCase):
    def test_reg_small_run(self):
        events = [
            make("1", "u", 0, page="/a"), make("1", "u", 10, page="/a"), make("2", "u", 500, page="/b"),
            make("3", "v", 0, page="/a"), make("4", "u", 99999, page="/a"),
        ]
        result = run(events, gap_ms=1000, funnel_steps=["/a", "/b"], top_n=2)
        self.assertEqual(result, {
            "events": 4, "duplicates": 1, "sessions": 3, "bounce_rate": 2 / 3,
            "top_pages": [("/a", 3), ("/b", 1)], "funnel": [2, 1],
        })


# ---------------------------------------------------------------------------------------------
# Speed. Every case builds 40,000-event inputs from a fixed seed, times the library call, and compares
# the result with a simple dict-based reference written here.

PRELUDE = r'''
import hashlib, json, os, random, sys, time
sys.path.insert(0, os.getcwd())
from tracelens.events import Event, sort_key

def digest(obj):
    return hashlib.md5(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, time.perf_counter() - t0

def report(result, reference, elapsed):
    print(json.dumps({"same": digest(result) == digest(reference), "seconds": elapsed}))
'''

CASES = {
    "dedupe": r'''
from tracelens.ingest.dedupe import dedupe
rng = random.Random(11)
events = [Event(f"e{i}", f"u{rng.randrange(8000)}", rng.randrange(10**7), "view", "/p", rng.randrange(4), i)
          for i in range(40000)]
for j in range(20000):
    base = events[rng.randrange(40000)]
    events.append(Event(base.id, base.user, base.ts + rng.randrange(0, 5000), "view", "/p", rng.randrange(4), 10**6 + j))
rng.shuffle(events)
result, elapsed = timed(dedupe, events)
first = {}
for e in sorted(events, key=sort_key):
    first.setdefault(e.id, e)
reference = [[e.id, e.ts, e.shard, e.seq] for e in sorted(first.values(), key=sort_key)]
report([[e.id, e.ts, e.shard, e.seq] for e in result], reference, elapsed)
''',
    "sessions": r'''
from tracelens.analysis.sessions import sessionize
rng = random.Random(12)
events = [Event(f"e{i}", f"u{rng.randrange(20000)}", rng.randrange(0, 3 * 10**7), "view" if i % 9 else "ping",
                f"/p{rng.randrange(50)}", rng.randrange(3), i) for i in range(40000)]
rng.shuffle(events)
result, elapsed = timed(sessionize, events, 600000)
latest, ref = {}, []
for e in sorted((e for e in events if e.kind != "ping"), key=sort_key):
    s = latest.get(e.user)
    if s is not None and e.ts - s["end"] <= 600000:
        s["end"] = e.ts; s["events"] += 1
        if e.page not in s["pages"]: s["pages"].append(e.page)
    else:
        s = {"id": "s_%06d" % (len(ref) + 1), "user": e.user, "start": e.ts, "end": e.ts, "events": 1, "pages": [e.page]}
        ref.append(s); latest[e.user] = s
report([[s.id, s.user, s.start, s.end, s.events, s.pages] for s in result],
       [[s["id"], s["user"], s["start"], s["end"], s["events"], s["pages"]] for s in ref], elapsed)
''',
    "top_pages": r'''
from tracelens.reports.pages import top_pages
rng = random.Random(13)
events = [Event(f"e{i}", f"u{rng.randrange(5000)}", i, "view" if i % 7 else "click", f"/page/{rng.randrange(30000)}", 0, i)
          for i in range(40000)]
result, elapsed = timed(top_pages, events, 25)
counts = {}
for e in events:
    if e.kind == "view":
        counts[e.page] = counts.get(e.page, 0) + 1
reference = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:25]
report([list(r) for r in result], [list(r) for r in reference], elapsed)
''',
    "top_pages_unique": r'''
from tracelens.reports.pages import top_pages
rng = random.Random(14)
events = [Event(f"e{i}", f"u{rng.randrange(3000)}", i, "view", f"/page/{rng.randrange(25000)}", 0, i) for i in range(40000)]
events += [Event(f"h{i}", f"u{i % 4000}", i, "view", "/home", 0, i) for i in range(20000)]
result, elapsed = timed(top_pages, events, None, True)
viewers = {}
for e in events:
    viewers.setdefault(e.page, set()).add(e.user)
reference = sorted(((p, len(v)) for p, v in viewers.items()), key=lambda kv: (-kv[1], kv[0]))
report([list(r) for r in result], [list(r) for r in reference], elapsed)
''',
    "funnel": r'''
from tracelens.analysis.funnel import funnel
rng = random.Random(15)
steps = ["/a", "/b", "/c"]
pages = steps + ["/x", "/y"]
events = [Event(f"e{i}", f"u{rng.randrange(20000)}", rng.randrange(10**6), "view" if i % 11 else "click",
                rng.choice(pages), rng.randrange(2), i) for i in range(40000)]
result, elapsed = timed(funnel, events, steps)
by_user = {}
for e in sorted((e for e in events if e.kind == "view"), key=sort_key):
    by_user.setdefault(e.user, []).append(e.page)
reference = [0, 0, 0]
for pages_seen in by_user.values():
    step = 0
    for p in pages_seen:
        if step < 3 and p == steps[step]:
            step += 1
    for i in range(step):
        reference[i] += 1
report(result, reference, elapsed)
''',
    "pipeline": r'''
from tracelens import run
rng = random.Random(16)
steps = ["/home", "/pricing", "/signup"]
events = [Event(f"e{i}", f"u{rng.randrange(15000)}", rng.randrange(0, 2 * 10**7), "view" if i % 8 else "ping",
                rng.choice(steps + [f"/page/{rng.randrange(20000)}"]), rng.randrange(3), i) for i in range(40000)]
events += [Event(events[j].id, events[j].user, events[j].ts + 7, events[j].kind, events[j].page, 5, 10**6 + j)
           for j in range(0, 40000, 4)]
rng.shuffle(events)
result, elapsed = timed(run, events, 900000, steps, 10)
first = {}
for e in sorted(events, key=sort_key):
    first.setdefault(e.id, e)
unique = sorted(first.values(), key=sort_key)
latest, nsessions, single = {}, 0, 0
sizes = {}
for e in unique:
    if e.kind == "ping":
        continue
    s = latest.get(e.user)
    if s is not None and e.ts - s[0] <= 900000:
        s[0] = e.ts; s[1] += 1
    else:
        s = [e.ts, 1, nsessions]; latest[e.user] = s; nsessions += 1
    sizes[s[2]] = s[1]
single = sum(1 for n in sizes.values() if n == 1)
views = {}
for e in unique:
    if e.kind == "view":
        views[e.page] = views.get(e.page, 0) + 1
top = sorted(views.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
by_user = {}
for e in unique:
    if e.kind == "view":
        by_user.setdefault(e.user, []).append(e.page)
fun = [0, 0, 0]
for seen in by_user.values():
    step = 0
    for pg in seen:
        if step < 3 and pg == steps[step]:
            step += 1
    for i in range(step):
        fun[i] += 1
reference = {"events": len(unique), "duplicates": 40000 + 10000 - len(unique), "sessions": nsessions,
             "bounce_rate": single / nsessions, "top_pages": [list(r) for r in top], "funnel": fun}
result["top_pages"] = [list(r) for r in result["top_pages"]]
report(result, reference, elapsed)
''',
}

CHILD_TIMEOUT_S = 20
BUDGET_S = 8.0


def run_case(name):
    script = PRELUDE + CASES[name]
    try:
        proc = subprocess.run([sys.executable, "-B", "-c", script], cwd=os.getcwd(), capture_output=True,
                              text=True, timeout=CHILD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise AssertionError(f"{name}: no answer after {CHILD_TIMEOUT_S}s on 40,000 events") from None
    if proc.returncode != 0:
        raise AssertionError(f"{name} crashed:\n{proc.stderr[-800:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestSpeedOn40000Events(unittest.TestCase):
    def check(self, name):
        out = run_case(name)
        self.assertTrue(out["same"], f"{name}: result differs from the reference")
        self.assertLess(out["seconds"], BUDGET_S, f"{name} took {out['seconds']:.1f}s")
        return out

    def test_dedupe(self):
        self.check("dedupe")

    def test_sessionize(self):
        self.check("sessions")

    def test_top_pages_with_many_pages(self):
        self.check("top_pages")

    def test_top_pages_unique_users(self):
        self.check("top_pages_unique")

    def test_funnel_with_many_users(self):
        self.check("funnel")

    def test_whole_pipeline(self):
        self.check("pipeline")


if __name__ == "__main__":
    unittest.main()

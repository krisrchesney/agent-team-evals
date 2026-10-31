# t29-hot-path: where each hidden-test rule is shown

The repo is a 3,000-line event-analytics library. Four stages that `pipeline.run` calls are quadratic,
each in a different way (a list used as a set, a linear search for a user's latest session, a linear
search for a page's counter, a full scan of the events per user). Nothing in the repo says which ones.
This file is outside `repo/`, so agents never see it.

## Time budgets

Every speed test builds its 40,000-event input from a fixed seed in a **child process**, times the
library call there, and compares the answer with a simple dict-based reference written in the test.

- Budget: the library call must take less than **8 s** (`BUDGET_S`) and the child gets a hard limit of
  **20 s** (`CHILD_TIMEOUT_S`), so a quadratic version fails in 20 s instead of hanging.
- Measured on the reference solution: well under 1 s per case (pure Python, one pass plus a sort), so
  the budget is 10x or more above what any O(n log n) fix needs. The starting code takes minutes at
  this size (about 6e8 to 1e9 comparisons per stage).
- `test_timeout_s` is 240: the snapshot run spends up to 20 s on each of the six speed tests.
- The speed cases are chosen so only the quadratic term matters: many distinct ids (dedupe), many users
  and thus many sessions (sessions), many distinct pages (top pages, with and without unique users), many
  users (funnel). A run with few users or pages would be fast even in the starting code.

## Rules

The behaviour tests (`test_reg_*`) pass on the starting code by design: they pin what the rewrite must preserve. Only the six speed tests fail there.

| Test group | Rule | Shown by (repo/) |
|---|---|---|
| `TestDedupe` | the earliest copy by `(ts, shard, seq)` is kept, ties go to the lower shard then seq, the result is sorted by that key, the input is not changed, the id alone identifies an event | `ingest/dedupe.py` docstring; `events.sort_key` |
| `TestSessions` | events are processed in `sort_key` order whatever the input order; exactly `gap_ms` continues a session; the gap is measured from the session's last event; pings are ignored; ids `s_000001...` in start order; pages once each in first-visit order | `analysis/sessions.py` docstring and `IGNORED_KINDS` |
| `TestTopPages` | only views count, ties by page name, `n=None` means all, `unique_users` counts each user once per page | `reports/pages.py` docstring |
| `TestFunnel` | steps are matched in order on the sorted stream, repeats do not count twice, only views count, users are independent | `analysis/funnel.py` docstring |
| `TestPipeline` | the combined result keeps its shape and numbers | `pipeline.py`, `tests/test_basic.py` |
| `TestSpeedOn40000Events` | each of the four stages and the whole pipeline finish within the budget and give exactly the reference answer | prompt ("a few seconds at most for 40,000 events"; "results must not change at all, including ties") |

What makes it hard: four separate hot spots, none flagged, in a repo where most other code is already
linear; the behaviour that must survive the rewrite (tie-breaking, ping handling, the gap boundary, id
numbering, first-visit page order) lives in docstrings and loop bodies. A fix that uses a set for
`seen` and a dict for the latest session but forgets the page-counter or funnel stage fails those tests;
a fix that reorders or changes tie-breaking fails the small behaviour tests and the reference comparison.

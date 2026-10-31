# ratelimit spec

Times are floats in seconds. `Decision` (see `decision.py`) has `allowed`, `limit`, `remaining`,
`retry_after` and `reset_after`. Bad arguments raise `ValueError`; the package's own errors are in
`errors.py`.

## Rules (`rules.py`)

A rule holds its settings and is pure: `evaluate(state, now, cost, max_skew)` returns
`(decision, new_state)`, never changes the `state` dict it was given, and does not use a store or a
clock. `state` is `None` for a key that was never seen. `new_state` is a JSON-serialisable dict.

`cost` is an `int` (not a `bool`) >= 1, else `ValueError`.

### TokenBucket(capacity, refill_per_sec)

`capacity` is an `int` >= 1 (not a `bool`); `refill_per_sec` is a number > 0. Otherwise `ValueError`.

State: `{"tokens": float, "updated": float}`. A key never seen starts full: `tokens = capacity`,
`updated = now`.

To evaluate, first bring the state up to date:

1. If `updated > now + max_skew` (the stored time is too far in the future, so the clock went
   backwards), set `updated = now`. Tokens are kept.
2. `elapsed = max(0, now - updated)`; `tokens = min(capacity, tokens + elapsed * refill_per_sec)`.
3. `updated = max(updated, now)`. (So a stored time that is in the future by at most `max_skew` stays
   as it is and nothing is refilled until the clock passes it.)

Then decide:

- `cost > capacity` can never succeed: not allowed, `retry_after = None`, the updated state is returned.
- `tokens >= cost` (plain comparison, no tolerance): allowed, `tokens -= cost`, `retry_after = 0.0`.
- otherwise not allowed, tokens unchanged, `retry_after = (cost - tokens) / refill_per_sec`.

Decision fields: `limit = capacity`, `remaining = int(tokens)` (floor, after any deduction),
`reset_after = (capacity - tokens) / refill_per_sec` (after any deduction).

`is_idle(state, now, max_skew)`: true when the state, brought up to date as above, has `tokens ==
capacity` (a `None` state is idle).

### SlidingWindow(limit, window)

`limit` is an `int` >= 1 (not a `bool`); `window` is a number > 0. Otherwise `ValueError`.

State: `{"hits": [float, ...]}`, the times of counted hits, ascending. `None` means no hits.

To evaluate, first bring the state up to date:

1. Any hit older than the window is dropped: a hit at time `t` is expired when `t <= now - window`.
2. Any hit with `t > now + max_skew` is moved to `now`. Hits that are in the future by at most
   `max_skew` stay as they are.
3. The list is sorted.

Then decide, with `count = len(hits)`:

- `cost > limit` can never succeed: not allowed, `retry_after = None`, the updated state is returned.
- `count + cost <= limit`: allowed. `cost` hits at time `now` are added (kept sorted), `retry_after = 0.0`.
- otherwise not allowed, no hit is added. `retry_after` is the time until enough hits have expired for
  the request to fit: with `i = count + cost - limit - 1`, it is `max(0.0, hits[i] + window - now)`.

Decision fields: `limit = limit`, `remaining = limit - len(hits)` after any addition (never below 0),
`reset_after = max(0.0, hits[-1] + window - now)` after any addition, `0.0` if there are no hits.

`is_idle`: true when the state, brought up to date as above, has no hits (`None` is idle).

## Stores (`store.py`)

`MemoryStore` is finished. `JsonFileStore(path)` has the same interface and keeps everything in one
JSON file with this layout (keys sorted, `json.dumps(..., sort_keys=True)`):

    {"version": 1, "rules": {"<rule name>": {"<key>": <state>}}}

- It reads the file again on every call, so a change made by another process or another store object on
  the same path is seen at once. `set`, `delete` and `delete_rule` read, change and rewrite the file.
- A missing file is an empty store. Reading never creates the file. `delete` and `delete_rule` do not
  create it either.
- Writes are atomic: write the whole new content to `<path>.tmp`, then `os.replace` it over `path`. No
  `.tmp` file is left behind. Missing parent directories are created by `set`.
- A rule with no keys left is removed from the file.
- If the file exists but is not valid JSON, or is not an object with `"version": 1` and a `"rules"`
  object, every method raises `StoreCorrupt` and the file is left untouched (including by `set`).
- `get` returns a fresh dict (or `None`), `keys` returns sorted keys (empty list for an unknown rule).

## Limiter (`limiter.py`)

`Limiter(rules, store=None, clock=None, max_skew=2.0)` is already constructed for you. `rules` maps rule
names to rule objects. `hit`, `peek`, `hit_all` and `purge` read the clock **once** and use that `now` for everything
they do (`reset` does not read it). `key` must be a non-empty `str`, else `ValueError`. A rule name that is not in `rules` raises
`UnknownRule`. `cost` is validated by the rule (and a bad `cost` must leave the store unchanged).
Argument checks (rule name, key, cost) happen before anything is read from or written to the store.

- `hit(rule, key, cost=1)`: loads the state, calls the rule's `evaluate`, saves the new state
  (whether or not the request was allowed), returns the decision.
- `peek(rule, key, cost=1)`: the decision `hit` would return right now; saves nothing.
- `hit_all(pairs, cost=1)`: `pairs` is a non-empty list of `(rule, key)` with no repeated pair, else
  `ValueError`. Every pair is evaluated with the same `cost` and the same `now`. If all are allowed,
  all new states are saved and the returned decision is the one with the smallest `remaining` (the
  first of them on a tie). If any is denied, **nothing is saved** and the returned decision is the
  denied one with the largest `retry_after` (a `None` counts as larger than any number; the first on a
  tie).
- `reset(rule, key=None)`: forgets one key, or every key of the rule when `key` is `None`. Returns `None`.
- `purge()`: removes every stored `(rule, key)` whose rule says `is_idle` (using the rules the limiter
  has; stored data for rule names it does not know is left alone). Returns how many were removed.

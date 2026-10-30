`breakerkit.CircuitBreaker` protects calls to a flaky dependency. Today it only counts failures and
reopens after a pause. Rewrite it to meet this spec. All time comes from the injected `clock`, a
zero-argument callable returning seconds as a float; tests use a fake clock.

**Construction**

R1. `CircuitBreaker(failure_threshold, window, cooldown, half_open_successes=1, probe_limit=1,
    expected=(Exception,), clock=time.monotonic)`. `failure_threshold` is an int >= 1, `window` and
    `cooldown` are numbers > 0, `half_open_successes` is an int >= 1 and `probe_limit` is an int >=
    `half_open_successes`. Anything else raises `ValueError`. The `state` property is one of the
    strings `"closed"`, `"open"`, `"half_open"`, and a new breaker is closed.

**Closed**

R2. In the closed state `allow()` returns `True`. `record_failure()` notes the current time. A failure
    counts toward the threshold only while `now - failure_time < window` (a failure exactly `window`
    old no longer counts). The breaker opens, at the current time, on the failure that brings the
    number of counted failures to `failure_threshold`. `record_success()` while closed forgets all
    recorded failures.

**Open**

R3. While open, `allow()` returns `False`, and `record_failure()` and `record_success()` do nothing
    (they are late results from calls started earlier). The state is a function of the clock: as soon
    as `now - opened_at >= cooldown` (equal counts) it is `"half_open"`, no matter which method or
    property is asked first. Results recorded at or after that moment are half-open results (R4, R5).

**Half-open**

R4. In the half-open state `allow()` returns `True` for the first `probe_limit` calls made since the
    breaker became half-open and `False` afterwards. Every call that returns `True` uses up one probe.
R5. A failure while half-open opens the breaker again at once, with a new `opened_at` (a full new
    cooldown). Each success while half-open counts, and the `half_open_successes`-th success closes
    the breaker. Every time the breaker becomes half-open it starts with zero probes used and zero
    successes, and every time it becomes closed or open it starts with no recorded failures.

**Reporting**

R6. `transitions` returns a list of `(time, from_state, to_state)` tuples, one for each state change
    in order, as a copy. The time of a move to open, to closed, or from half-open to open is the
    clock reading when it happened. The time of the move from open to half-open is
    `opened_at + cooldown`, even if the breaker is only looked at later. Each move is listed once.
R7. `retry_after()` returns how many seconds are left until an open breaker becomes half-open, never
    below `0.0`, and `0.0` in any other state.
R8. `reset()` makes the breaker closed with no recorded failures. It adds a transition only if the
    state actually changed.

**Wrapping calls**

R9. `call(fn, *args, **kwargs)` raises `CircuitOpenError` (exported from `breakerkit`) without calling
    `fn` if `allow()` is `False`. Otherwise it calls `fn` and returns its result after
    `record_success()`. If `fn` raises an exception that is an instance of `expected`, it calls
    `record_failure()` and re-raises. Any other exception is re-raised and counts as neither a success
    nor a failure; if that call was using a half-open probe, the probe is given back.

Standard library only. Existing tests are in `tests/`.

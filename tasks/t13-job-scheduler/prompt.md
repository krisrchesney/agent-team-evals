`jobkit.Scheduler` runs jobs one at a time with priorities, retries and dependencies. Time comes
from a clock object with `now()` and `sleep(seconds)`; `jobkit.FakeClock` is a clock for tests
whose `sleep` just moves `now()` forward. Users report that some job sets run in the wrong order,
retry the wrong number of times, or skip jobs they should not. Fix the library so that it meets
this spec:

1. `Scheduler(clock, base_delay=1.0, max_delay=60.0)`.
   `submit(job_id, fn, priority=0, deps=(), max_retries=0)` registers a job; `fn` takes no
   arguments. A duplicate `job_id` raises `ValueError`, and so does a `max_retries` that is not an
   `int >= 0`. `deps` are job ids and may name jobs that are submitted later. `run()` checks the
   dependencies before it runs anything: an unknown job id raises `KeyError`, a dependency cycle
   raises `ValueError`, and in both cases no job runs.
2. Among the jobs that are ready, `run()` runs the one with the lowest `priority` number. Jobs with
   the same priority run in the order they were submitted. A job's place in that order never
   changes: a job that is retried keeps the place it was submitted at.
3. A job whose `fn` raises an `Exception` has failed that attempt. A job with `max_retries=n` is
   attempted at most `n + 1` times. When an attempt fails and retries are left, the k-th retry
   (k = 1 for the first) becomes ready `min(max_delay, base_delay * 2 ** (k - 1))` seconds after
   the moment that attempt failed, measured with `clock.now()` when `fn` raised (`fn` itself may
   take time, for example by calling `clock.sleep`). When a job succeeds, its status is `done`.
   When it fails with no retries left, its status is `failed`.
4. A job is ready when all its dependencies are `done` and, if it is a retry, its ready time has
   come (`clock.now()` at that moment is at or past it). Readiness is judged each time `run()`
   picks the next job, using the current `clock.now()`. A job that is waiting out a retry delay
   never holds up other ready jobs. When no job is ready but some are waiting for a retry delay,
   `run()` calls `clock.sleep(...)` once for exactly the time until the earliest of them is ready.
   `run()` returns when no job is ready or waiting.
5. A job runs only after all its dependencies are `done`. A dependency that failed an attempt but
   then succeeded on a retry counts as `done`. When a job ends as `failed`, every job that depends
   on it, directly or through other jobs, gets the status `skipped` and never runs.
6. `run()` returns a dict `{job_id: status}` for every submitted job, each status one of `done`,
   `failed` or `skipped`. `scheduler.results` maps the id of each `done` job to what its `fn`
   returned, and `scheduler.errors` maps the id of each `failed` job to the exception from its
   last attempt.

Keep the public names and signatures as they are. Use only the Python standard library.
Existing tests are in `tests/`.

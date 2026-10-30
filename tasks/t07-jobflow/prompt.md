`jobflow` runs the jobs of a JSON spec in dependency order (`runner.run`), prints a report
(`report.py`) and has a CLI (`python -m jobflow SPEC.json [--json]`). Today a job that fails
makes everything that depends on it be skipped, and nothing is ever retried. Extend it so that:

1. `Job` gets four more fields after `args`, in this order: `retries=0` (int), `backoff=0.0`
   (seconds), `allow_failure=False` and `when="success"`. A spec job may set the same keys
   (`"retries": 2`, ...), and `load_jobs` passes them through.
2. `load_jobs` validates the new keys and raises `ConfigError` with exactly these messages
   (`x` is the job's name): `job 'x': retries must be a non-negative integer` (booleans and floats
   are not integers), `job 'x': backoff must be a non-negative number` (ints and floats are fine,
   booleans are not), `job 'x': allow_failure must be true or false`, and
   `job 'x': when must be one of success, always, failure`.
3. `run(jobs, actions=None, sleep=time.sleep, only=None)`. A job's action is tried up to
   `1 + retries` times and stops at the first try that returns without raising. Then the result is
   `ok`, with `attempts` set to the number of tries and `output` taken from that try. If every try
   raises, the result is `failed`, `attempts == 1 + retries`, and `error` is the message of the last
   exception (as today). An unknown action is a `failed` result after one try: it is never retried
   and `attempts == 1`. A skipped job has `attempts == 0`. `Result` gets the fields `attempts`
   (default 0) and `stage` (default 0).
4. Before retry number `k` (`k = 1, 2, ...`) `run` calls `sleep(backoff * 2 ** (k - 1))`. It never
   sleeps before the first try or after the last failed try, and does not call `sleep` at all when
   the job's `backoff` is 0.
5. `when` decides whether a job runs once its dependencies have finished. With `"success"` (the
   default) it runs only if every dependency is `ok` or is `failed` with `allow_failure` set;
   otherwise it is skipped with the reason `dependency '<name>' <status>`, naming the first
   dependency (in the order the job lists them) that blocks it and that dependency's status
   (`failed` or `skipped`). A job that fails is still `failed` when `allow_failure` is set; the flag
   only stops it from blocking the jobs that depend on it.
6. With `when: "always"` a job runs whatever its dependencies' results are (it is still ordered
   after them). With `when: "failure"` it runs only if at least one of its direct dependencies has
   status `failed` (whether or not that dependency allows failure); otherwise it is skipped with the
   reason `no dependency failed`, and so is a `when: "failure"` job that has no dependencies.
7. `only` is `None` (run everything) or a non-empty list of job names. `run` then runs just
   those jobs and everything they depend on, directly or not, and returns results only for those
   jobs, in the usual order. An unknown name raises `ConfigError("unknown job '<name>'")`.
8. `Result.stage` is the job's stage: 1 for a job without dependencies, otherwise 1 plus the highest
   stage among its dependencies. It is set on every result, skipped ones included.
9. In the text report, an `ok` or `failed` line gets the suffix ` (<n> attempts)` when its
   `attempts` is more than 1 (after the error text for a failed job, e.g.
   `b: failed: boom (3 attempts)`). Nothing else in the text report changes. `to_dicts` adds the keys
   `attempts` and `stage` to every dict and keeps the others.
10. The CLI gets a repeatable `--only NAME` option that is passed to `run` as `only`. An unknown
    name prints `jobflow: error: unknown job 'NAME'` to stderr, nothing to stdout, and returns 2 like
    other config errors. The exit status is now 1 if any job has status `failed` and does not have
    `allow_failure` set, and 0 otherwise (skipped jobs alone do not make it 1).
11. Everything else keeps working as it does today, for specs that use none of the new keys:
    run order (jobs that are ready run in declaration order), cycle and unknown-dependency errors,
    transitive skipping, and the text and JSON output.

Standard library only. Existing tests are in `tests/`.

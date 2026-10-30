"""One unit of work and its bookkeeping."""

PENDING = "pending"    # never attempted yet
WAITING = "waiting"    # failed an attempt, a retry is scheduled
DONE = "done"
FAILED = "failed"
SKIPPED = "skipped"


class Job:
    def __init__(self, job_id, fn, priority, deps, max_retries, seq):
        self.id = job_id
        self.fn = fn
        self.priority = priority
        self.deps = tuple(deps)
        self.max_retries = max_retries
        self.seq = seq                 # position in submission order
        self.status = PENDING
        self.failures = 0
        self.ready_at = float("-inf")  # when the next attempt may start
        self.result = None
        self.error = None

    @property
    def finished(self):
        return self.status in (DONE, FAILED, SKIPPED)

    def sort_key(self):
        return (self.priority, self.seq)

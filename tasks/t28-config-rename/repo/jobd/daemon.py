"""The daemon: wires settings, queue, pool and registry, and runs jobs to completion."""
from . import job as jobs
from . import retry
from .config import loader
from .deadletter import DeadLetters
from .journal import Journal
from .queue import JobQueue
from .registry import HandlerRegistry
from .runtime.backpressure import Backpressure
from .runtime.limits import check_consistency
from .runtime.pool import WorkerPool
from .runtime.scheduler import Scheduler


class Daemon:
    def __init__(self, settings=None):
        self.settings = check_consistency(settings or loader.load(environ={}))
        self.queue = JobQueue(self.settings.queue_size)
        self.pool = WorkerPool(self.settings)
        self.scheduler = Scheduler(self.settings)
        self.backpressure = Backpressure(self.settings)
        self.registry = HandlerRegistry()
        self.dead = DeadLetters()
        self.journal = Journal()
        self.finished = []

    def submit(self, handler, payload=None, priority=5):
        self.registry.get(handler)
        if self.backpressure.should_reject(self.queue.depth()):
            from .errors import Conflict
            raise Conflict("queue is full, try again later", field="queue")
        job = jobs.create(handler, payload, priority, self.settings.max_payload_kb)
        self.queue.push(job)
        return job

    def tick(self):
        """Start what fits, run it, and requeue or bury failures. Returns the number of jobs run."""
        batch = self.scheduler.take_batch(self.queue, in_flight=self.pool.busy())
        started = []
        for job in batch:
            worker = self.pool.submit(job, self.registry.get(job.handler))
            if worker is None:
                self.queue.push(job)
                continue
            self.journal.record("started", job)
            started.append(job)
        for job, ok in self.pool.drain():
            if ok:
                self.journal.record("finished", job)
                self.finished.append(job)
            elif retry.after_failure(self.settings, job, self.queue, self.dead) == "dead":
                self.journal.record("dead", job)
        return len(started)

    def run_until_idle(self, max_ticks=1000):
        ticks = 0
        while self.queue.depth() and ticks < max_ticks:
            self.tick()
            ticks += 1
        return ticks

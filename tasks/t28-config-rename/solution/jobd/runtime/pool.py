"""The worker pool: a fixed set of workers that jobs are handed to."""
from ..worker import Worker


class WorkerPool:
    def __init__(self, settings):
        self.settings = settings
        self.size = settings.worker_threads
        self.workers = [Worker(f"{settings.pool_name}-{i}") for i in range(self.size)]
        self._next = 0

    def idle(self):
        return [w for w in self.workers if not w.busy]

    def busy(self):
        return sum(1 for w in self.workers if w.busy)

    def submit(self, job, handler):
        """Give the job to the next idle worker (round robin). Returns the worker, or None if all are busy."""
        for _ in range(self.size):
            worker = self.workers[self._next % self.size]
            self._next += 1
            if not worker.busy:
                worker.start(job, handler)
                return worker
        return None

    def drain(self):
        """Finish every running job and return the workers' completed results."""
        results = []
        for worker in self.workers:
            if worker.busy:
                results.append(worker.finish())
        return results

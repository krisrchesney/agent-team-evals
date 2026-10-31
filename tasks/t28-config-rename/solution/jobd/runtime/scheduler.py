"""Deciding how many queued jobs to start right now."""


class Scheduler:
    def __init__(self, settings):
        self.settings = settings
        # Two jobs per worker may be in flight, so a worker never waits for its next job.
        self.max_in_flight = settings.worker_threads * 2

    def room(self, in_flight):
        return max(0, self.max_in_flight - in_flight)

    def take_batch(self, queue, in_flight):
        batch = []
        for _ in range(self.room(in_flight)):
            job = queue.pop()
            if job is None:
                break
            batch.append(job)
        return batch

    def describe(self):
        return f"{self.max_in_flight} jobs in flight for {self.settings.worker_threads} workers"

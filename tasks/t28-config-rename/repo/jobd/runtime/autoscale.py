"""How many workers are worth running for the current queue depth."""
import math


class Autoscaler:
    JOBS_PER_WORKER = 10

    def __init__(self, settings):
        self.floor = 1
        self.ceiling = settings.queue_workers

    def desired(self, queue_depth):
        wanted = max(self.floor, math.ceil(queue_depth / self.JOBS_PER_WORKER))
        return min(self.ceiling, wanted)

    def advice(self, queue_depth, running):
        want = self.desired(queue_depth)
        if want > running:
            return f"start {want - running} more worker(s)"
        if want < running:
            return f"{running - want} worker(s) could be idle"
        return "no change"

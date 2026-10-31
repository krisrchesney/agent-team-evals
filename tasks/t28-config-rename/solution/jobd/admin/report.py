"""`jobd report`: a one-screen summary for the on-call channel."""
from .. import capacity, health


def summary(settings, pool, queue, average_runtime_s=2.0):
    rep = health.report(settings, pool, queue)
    per_minute = capacity.jobs_per_minute(settings, average_runtime_s)
    lines = [
        f"pool {rep['pool']} is {rep['status']}",
        f"{settings.worker_threads} worker(s), {rep['busy']} busy",
        f"queue holds {rep['queue_depth']} of {settings.queue_size}",
        f"capacity about {per_minute:.0f} jobs/min at {average_runtime_s:g}s per job",
    ]
    if queue.depth():
        wait = capacity.drain_time_s(settings, queue.depth(), average_runtime_s)
        lines.append(f"the queue would drain in about {wait:.0f}s")
    return "\n".join(lines) + "\n"

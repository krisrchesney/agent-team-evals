"""`jobd status`: a few lines for a human."""
from .. import health


def format_status(settings, pool, queue):
    rep = health.report(settings, pool, queue)
    return "\n".join([
        f"pool {rep['pool']}: {rep['status']}",
        f"workers: {rep['busy']}/{settings.worker_threads} busy",
        f"queue: {rep['queue_depth']}/{settings.queue_size} jobs",
        f"retries: up to {settings.retry_limit}, first after {settings.retry_backoff_s:g}s",
    ]) + "\n"

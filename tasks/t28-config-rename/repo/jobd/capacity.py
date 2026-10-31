"""Back-of-the-envelope capacity numbers for sizing a pool."""
import math


def jobs_per_minute(settings, average_runtime_s):
    """How many jobs a full pool finishes in a minute if each takes `average_runtime_s`."""
    if average_runtime_s <= 0:
        raise ValueError("average_runtime_s must be positive")
    return settings.queue_workers * 60.0 / average_runtime_s


def drain_time_s(settings, queued, average_runtime_s):
    """Seconds to empty a queue of `queued` jobs, ignoring retries."""
    rate_per_s = settings.queue_workers / average_runtime_s
    return queued / rate_per_s


def workers_needed(arrival_per_s, average_runtime_s, headroom=1.25):
    """Workers to keep up with `arrival_per_s` jobs a second, with some headroom."""
    return max(1, math.ceil(arrival_per_s * average_runtime_s * headroom))


def fits(settings, arrival_per_s, average_runtime_s):
    return workers_needed(arrival_per_s, average_runtime_s) <= settings.queue_workers

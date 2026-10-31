"""The health report served on /healthz."""


def report(settings, pool, queue):
    busy = pool.busy()
    return {
        "status": "ok" if queue.depth() < settings.queue_size else "degraded",
        "pool": settings.pool_name,
        "workers": settings.worker_threads,
        "busy": busy,
        "idle": settings.worker_threads - busy,
        "queue_depth": queue.depth(),
        "queue_size": settings.queue_size,
    }


def is_healthy(settings, pool, queue):
    return report(settings, pool, queue)["status"] == "ok"

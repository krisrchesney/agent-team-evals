"""Numbers exported on the metrics endpoint."""


def snapshot(settings, pool, queue):
    labels = {"pool": settings.pool_name}
    return {
        "jobd_configured_workers": (settings.worker_threads, labels),
        "jobd_busy_workers": (pool.busy(), labels),
        "jobd_queue_depth": (queue.depth(), labels),
        "jobd_queue_capacity": (settings.queue_size, labels),
    }


def render(snap):
    """Text in the usual `name{label="value"} number` exposition format."""
    lines = []
    for name in sorted(snap):
        value, labels = snap[name]
        label_text = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        lines.append(f"{name}{{{label_text}}} {value}")
    return "\n".join(lines) + "\n"

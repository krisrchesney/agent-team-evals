"""Checks between settings that no single setting can make."""
from ..errors import ConfigError


def check_consistency(settings):
    """Raise ConfigError for combinations that cannot work together."""
    if settings.queue_size < settings.worker_threads:
        raise ConfigError(
            f"queue_size ({settings.queue_size}) must be at least worker_threads ({settings.worker_threads})",
            field="queue_size",
        )
    if settings.job_timeout_s < settings.heartbeat_s:
        raise ConfigError("job_timeout_s must not be shorter than heartbeat_s", field="job_timeout_s")
    if settings.shutdown_grace_s and settings.shutdown_grace_s < settings.poll_interval_s:
        raise ConfigError("shutdown_grace_s must not be shorter than poll_interval_s", field="shutdown_grace_s")
    return settings

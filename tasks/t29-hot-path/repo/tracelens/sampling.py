"""Deterministic sampling: the same user is always in or always out."""
import zlib


def bucket_of(user):
    """0..99, stable across runs and machines."""
    return zlib.crc32(user.encode("utf-8")) % 100


def keep_user(user, percent):
    return bucket_of(user) < percent


def sample(events, percent):
    """Events of the users who fall in the first `percent` buckets."""
    if percent >= 100:
        return list(events)
    return [e for e in events if keep_user(e.user, percent)]


def scale_up(count, percent):
    """Estimate the full count from a sampled one."""
    return round(count * 100 / percent)

"""Retry delays."""


def retry_delay(retry, base, cap):
    """Seconds to wait before the `retry`-th retry (1 for the first retry)."""
    return min(cap, base * 2 ** (retry - 1))

import hashlib

BUCKETS = 10_000


def bucket(salt, subject):
    """Place `subject` in one of BUCKETS stable buckets, 0 to 9999."""
    digest = hashlib.sha256(f"{salt}:{subject}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % BUCKETS

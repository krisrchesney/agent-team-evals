"""URL slug helpers."""


def slugify(text):
    """Turn a title into a URL slug."""
    return text.strip().lower().replace(" ", "-")

METERS = []


def meter(cls):
    """Register a meter class. The service builds one instance of each."""
    if cls in METERS or any(other.name == cls.name for other in METERS):
        raise ValueError(f"meter {cls.name!r} registered twice")
    METERS.append(cls)
    return cls


def build():
    """One instance of every registered meter, in priority order (lower first)."""
    return [cls() for cls in sorted(METERS, key=lambda cls: cls.priority)]
